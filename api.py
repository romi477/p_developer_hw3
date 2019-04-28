#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
import scoring


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2

GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field:
    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    def validate_field(self, value):
        raise NotImplementedError('Not implemented <is_valid_field()> method')
    
    def validate(self, value):
        if self.required and not value:
            raise ValueError('This field is required!')
        
        if not self.nullable and not value:
            raise ValueError('This field cannot be empty!')

        if value is None or value == '':
            return value

        self.validate_field(value)
        
        return value


class CharField(Field):
    def validate_field(self, value):
        if not isinstance(value, str):
            raise TypeError('"CharField" must be <str>!')


class ArgumentsField(Field):
    def validate_field(self, value):
        if value is not None and not isinstance(value, dict):
            raise TypeError('"ArgumentsField" must be <dict>!')


class EmailField(CharField):
    def validate_field(self, value):
        super().validate_field(value)
        if '@' not in value:
            raise ValueError('"EmailField" has incorrect value!')


class PhoneField(Field):
    def validate_field(self, value):
        if not isinstance(value, str) and not isinstance(value, int):
            raise TypeError('"PhoneField" must be <int> or <str>')
        
        if not str(value).startswith('7') and not len(str(value)) != 11:
            raise ValueError('"PhoneField" has incorrect value!')


class DateField(Field):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parse_date = None
    
    def validate_field(self, value):
        try:
            self.parse_date = datetime.datetime.strptime(value, '%d.%m.%Y')
        except Exception:
            raise


class BirthDayField(DateField, Field):
    def validate_field(self, value):
        super().validate_field(value)
        delta = datetime.datetime.now() - self.parse_date
        if delta.days / 365 > 70:
            raise ValueError('Age limit up to 70 years!')


class GenderField(Field):
    def validate_field(self, value):
        if value not in [UNKNOWN, MALE, FEMALE]:
            raise ValueError('"GenderField" has incorrect value!')


class ClientIDsField(Field):
    def validate_field(self, value):
        if not isinstance(value, list):
            raise TypeError('"ClientIDsField" must be <list>!')
        self.validate_array(value)
    
    @staticmethod
    def validate_array(array):
        for value in array:
            if not isinstance(value, int) or value < 0:
                raise ValueError('"ClientIDsField" has invalid data array!')


class RequestMeta(type):
    def __new__(cls, name, bases, attrs):
        field_instances = {}
        other_attrs = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                field_instances[key] = value
            else:
                other_attrs[key] = value
        new_cls = super().__new__(cls, name, bases, other_attrs)
        new_cls._fields_container = field_instances
        return new_cls


class Request(metaclass=RequestMeta):
    def __init__(self, params):
        self.params = params
        self.cleaned_data = {}
        self.errors = {}

    def validate_request(self):
        for field_name, field_instance in self._fields_container.items():
            params_value = self.params.get(field_name)
            try:
                clean_value = field_instance.validate(params_value)
            except Exception as ex:
                self.errors[field_name] = ex
            else:
                self.cleaned_data[field_name] = clean_value
                setattr(self, field_name, clean_value)

    def is_valid(self):
        return not self.errors

    @classmethod
    def data_init(cls, *args, **kwargs):
        class_instance = cls(*args, **kwargs)
        class_instance.validate_request()
        return class_instance


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode(encoding='utf_8')).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode(encoding='utf_8')).hexdigest()
    print('digest:', digest)
    if digest == request.token:
        return True
    return False


class OnlineScoreHandler:

    def execute_request(self, arguments, context, store):
        post_method = OnlineScoreRequest.data_init(arguments)

        if not post_method.is_valid():
            return INVALID_REQUEST, post_method.errors

        clean_dict = post_method.cleaned_data
        if not self.check_non_empty_pairs(clean_dict):
            return INVALID_REQUEST, {k: 'null' for k, v in clean_dict.items() if not v}
        
        context['has'] = [k for k, v in clean_dict.items() if v]
        
        scores = scoring.get_score(
            store,
            clean_dict.get('phone'),
            clean_dict.get('email'),
            clean_dict.get('birthday'),
            clean_dict.get('gender'),
            clean_dict.get('first_name'),
            clean_dict.get('last_name'),
        )

        if context.get('is_admin'):
            return OK, 42
        return OK, scores

    def check_non_empty_pairs(self, d):
        if d.get('phone') and d.get('email') or \
                d.get('first_name') and d.get('last_name') or \
                d.get('gender') and d.get('birthday'):
            return d


class ClientsInterestsHandler:

    def execute_request(self, arguments, context, store):
        post_method = ClientsInterestsRequest.data_init(arguments)

        if not post_method.is_valid():
            return INVALID_REQUEST, post_method.errors

        context['nclients'] = len(post_method.client_ids)

        interests_dict = {k: scoring.get_interests(store, k) for k in post_method.client_ids}

        return OK, interests_dict


def method_handler(request, context, store):
    handlers = {
        'online_score': OnlineScoreHandler,
        'clients_interests': ClientsInterestsHandler
    }
    
    post_ = MethodRequest.data_init(request['body'])
    
    if not post_.is_valid():
        return INVALID_REQUEST, post_.errors

    if not check_auth(post_):
        return FORBIDDEN, 'Forbidden!'
    
    context['is_admin'] = post_.is_admin
    
    handler = handlers[post_.method]
    
    code, response = handler().execute_request(post_.arguments, context, store)
    
    return code, response


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    code, response = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception(f"Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode(encoding='utf_8'))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
