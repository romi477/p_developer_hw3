import abc
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

r1 = {
    "account": "horns&hoofs",
    "login": "admin",
    "method": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
}

r2 = {
    "account2": "horns&hoofs",
    "login": "admin",
    "method": "clients_interests",
    "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
    "arguments": {"client_ids": [1, 2, 3, 4], "date": "20.07.2017"}
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

class Store:
    def __init__(self, cls):
        self.cls = cls


class FieldsContainer:
    def __init__(self, fields):
        self._fields = fields

    # def __repr__(self):
    #     return '\n'.join([f'{k} - {v}' for k, v in self._fields.items()])
    #
    # def get_field(self, key):
    #     return self._fields.get(key, 'Not found field')
    #
    # def has_field(self, field):
    #     return field in self._fields




class Field:
    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    def is_valid_field(self, value):
        print('Init <Field> validate')


class CharField(Field):
    pass


class ArgumentsField(Field):
    pass


class EmailField(CharField):
    pass


class PhoneField(Field):
    pass


class DateField(Field):
    pass


class BirthDayField(Field):
    pass


class GenderField(Field):
    pass


class ClientIDsField(Field):
    def is_valid_field(self, value):
        print('Init <Child> validate')
        super().is_valid_field(value)



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
        # new_cls.store = Store(new_cls)
        new_cls._fields_container = FieldsContainer(field_instances)
        return new_cls


class Request(metaclass=RequestMeta):
    def __init__(self, params):
        self.errors = {}
        self.params = params
        self._clean_fields = []

        for field_name, field_instance in self._fields_container._fields.items():
            params_value = self.params.get(field_name)
            if field_instance.required and field_name not in self.params:
                print(f'{field_name} - required BAD!')
                print('skip checking nullable')
                self.errors[field_name] = 'This field is required.'
            else:
                print(f'{field_name} - required OK!')
                if not field_instance.nullable and not params_value:
                    print(f'{field_name} - nullable BAD!')
                    self.errors[field_name] = 'This field cannot be empty.'
                else:
                    print(f'{field_name} - nullable OK!')
                    setattr(self, field_name, field_instance)
                    self._clean_fields.append(field_name)


    def is_valid(self):
        return not self.errors

    def execute_validate_fields(self):
        pass


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def execute_request(self, request, context, store):
        pass


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def execute_request(self, request, context, store):
        pass


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


def execute_request(model, request):
    data_instance = model(request)
    if not data_instance.is_valid():
        return data_instance.errors, INVALID_REQUEST


def method_handler(request):
    models = {
        'online_score': OnlineScoreRequest,
        'clients_interests': ClientsInterestsRequest
    }
    method_recv = MethodRequest(request['method'])

    if not method_recv.is_valid():
        return method_recv.errors, INVALID_REQUEST
    if not check_auth(method_recv):
        return 'Forbidden', FORBIDDEN

    model = models[method_recv.method]
    arguments = method_recv.arguments
    response, code = execute_request(model, arguments)

    return response, code

#
# if __name__ == '__main__':
#
#     method_handler()
#


