import abc
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
import scoring
from datetime import datetime


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

r1 = {
    "account": "horns&hoofs",
    "login": "admin",
    "method": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
}

r2 = {
    "account2": "horns&hoofs",
    "login2": "admin",
    "method": 123,
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": ["client_ids", [1, 2, 3, 4], "date", "20.07.2017"]
}


r3 = {
    "account": "horns&hoofs",
    "login": "",
    "method": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
}

r4 = {
    "account": "horns&hoofs",
    "login2": "",
    "method": "",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
}


r5 = {
    "account": "horns&hoofs",
    "login": "",
    "method2": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
}


r6 = {
    "account": "horns&hoofs",
    "login": "",
    "method": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
}

args1 = {
    "phone": "79175002040",
    "email": "stupnikov@otus.ru",
    "first_name": "Stas",
    "last_name": "Stupnikov",
    "birthday": "01.01.1990",
    "gender": 1
}

args2 = {
    "phone": "79175002040",
    "email": "stupnikov@otus.ru",
    "first_name": "Stas",
    "last_name": "Stupnikov",
    "birthday": "01.01.1990",
    "gender": 1
}


class Field:
    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable
        self.field_errors = {}

    def validate_field(self, value):
        raise NotImplementedError('Not implemented self.is_valid_field() method')

    def validate(self, value):
        if self.required and not value:
            raise ValueError('This field is required.')

        if not self.nullable and not value:
            raise ValueError('This field cannot be empty.')

        self.validate_field(value)


class CharField(Field):
    def validate_field(self, value):
        if value is not None and not isinstance(value, str):
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
        if not isinstance(value, str) or not isinstance(value, int):
            raise TypeError('"PhoneField" must be <int> or <str>' )

        if not str(value).startswith('7') and not len(str(value)) != 11:
            raise ValueError('"PhoneField" has incorrect value!')


class DateField(Field):
    def validate_field(self, value):
        try:
            self.parse_date = datetime.strptime(value, '%d.%m.%Y')
        except Exception:
            raise


class BirthDayField(DateField, Field):
    def validate_field(self, value):
        super().validate_field(value)
        delta = datetime.now() - self.parse_date
        if delta.days / 365 > 70:
            raise ValueError('Age limit up to 70 years!')
        
        
class GenderField(Field):
    def validate_field(self, value):
        if value not in [0, 1, 2]:
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
        self.errors = {}
        self._model_fields = []


    def validate_request(self):
        for field_name, field_instance in self._fields_container.items():
            params_value = self.params.get(field_name)
            try:
                field_instance.validate(params_value)
            except Exception as ex:
                self.errors[field_name] = ex


    def __repr__(self):
        return '\n'.join(self._model_fields)

    def is_valid(self):
        return not self.errors


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
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def online_score_handler(model, arguments):
    errors = {}
    model_instance = model(arguments)
    model_instance.validate_request()
    if not model_instance.is_valid():
        return model_instance.errors, INVALID_REQUEST
    for field_name in model_instance._model_fields:
        if not model_instance.__dict__[field_name].is_valid_field():
            errors[field_name] = 'Not valid!'

    return model_instance


def clients_interests_handler(model, arguments):
    pass


def method_handler(request):
    handlers = {
        'online_score': (online_score_handler, OnlineScoreRequest),
        'clients_interests': (clients_interests_handler, ClientsInterestsRequest)
    }

    method_recv = MethodRequest(request['method'])

    method_recv.validate_request()
    if not method_recv.is_valid():
        return method_recv.errors, INVALID_REQUEST
    if not check_auth(method_recv):
        return 'Forbidden', FORBIDDEN

    handler, model = handlers[method_recv.method]

    response, code = handler(model, method_recv.arguments)

    return response, code


