# -*- coding: utf-8 -*-

"""Decorators to check headers and method requirements for each Api calls"""

import collections
import json
from functools import wraps

from flask import request, make_response, jsonify, current_app

from flask_rest_jsonapi.errors import jsonapi_errors
from flask_rest_jsonapi.exceptions import JsonApiException
from flask_rest_jsonapi.utils import JSONEncoder


ALLOWED_HEADERS = {'application/vnd.api+json', 'application/json'}


def _is_list_like(iterable):
    return isinstance(iterable, collections.abc.Sequence) and not isinstance(iterable, str)


def check_headers(func):
    """Check headers according to jsonapi reference

    :param callable func: the function to decorate
    :return callable: the wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ('POST', 'PATCH'):
            has_content_type_header = 'Content-Type' not in request.headers
            if _is_list_like(request.headers['Content-Type']):
                header_set = set(request.headers['Content-Type'])
            else:
                header_set = set([request.headers['Content-Type']])
            header_is_allowed = ALLOWED_HEADERS.intersection(header_set)
            if not (has_content_type_header and header_is_allowed):
                error = json.dumps(jsonapi_errors([{'source': '',
                                                    'detail': "Content-Type header must be application/vnd.api+json",
                                                    'title': 'Invalid request header',
                                                    'status': '415'}]), cls=JSONEncoder)
                return make_response(error, 415, {'Content-Type': 'application/vnd.api+json'})
        if 'Accept' in request.headers:
            flag = False
            for accept in request.headers['Accept'].split(','):
                if accept.strip() in ALLOWED_HEADERS:
                    flag = False
                    break
                if 'application/vnd.api+json' in accept and accept.strip() != 'application/vnd.api+json':
                    flag = True
            if flag is True:
                error = json.dumps(jsonapi_errors([{'source': '',
                                                    'detail': ('Accept header must be application/vnd.api+json without'
                                                               'media type parameters'),
                                                    'title': 'Invalid request header',
                                                    'status': '406'}]), cls=JSONEncoder)
                return make_response(error, 406, {'Content-Type': 'application/vnd.api+json'})
        return func(*args, **kwargs)
    return wrapper


def check_method_requirements(func):
    """Check methods requirements

    :param callable func: the function to decorate
    :return callable: the wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        error_message = "You must provide {error_field} in {cls} to get access to the default {method} method"
        error_data = {'cls': args[0].__class__.__name__,
                      'method': request.method.lower()}

        if request.method != 'DELETE':
            if not hasattr(args[0], 'schema'):
                error_data.update({'error_field': 'a schema class'})
                raise Exception(error_message.format(**error_data))

        return func(*args, **kwargs)
    return wrapper


def jsonapi_exception_formatter(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        headers = {'Content-Type': 'application/vnd.api+json'}
        try:
            return func(*args, **kwargs)
        except JsonApiException as e:
            return make_response(jsonify(jsonapi_errors([e.to_dict()])),
                                 e.status,
                                 headers)
        except Exception as e:
            if current_app.config['DEBUG'] is True or current_app.config.get('PROPAGATE_EXCEPTIONS') is True:
                raise

            if 'sentry' in current_app.extensions:
                current_app.extensions['sentry'].captureException()

            exc = JsonApiException(getattr(e,
                                           'detail',
                                           current_app.config.get('GLOBAL_ERROR_MESSAGE') or str(e)),
                                   source=getattr(e, 'source', ''),
                                   title=getattr(e, 'title', None),
                                   status=getattr(e, 'status', None),
                                   code=getattr(e, 'code', None),
                                   id_=getattr(e, 'id', None),
                                   links=getattr(e, 'links', None),
                                   meta=getattr(e, 'meta', None))
            return make_response(jsonify(jsonapi_errors([exc.to_dict()])),
                                 exc.status,
                                 headers)
    return wrapper
