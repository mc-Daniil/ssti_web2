from functools import wraps
from flask import abort, g, request
from ..models import users


def fail(message, status=400):
    abort(status, description=message)


def body():
    value = request.get_json()
    if not isinstance(value, dict):
        fail('Expected a JSON object')
    return value


def string(data, key, maximum):
    value = data.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        fail(f'{key} must be a string of 1-{maximum} characters')
    return value.strip()


def authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        scheme, _, raw = request.headers.get('Authorization', '').partition(' ')
        if scheme.lower() != 'bearer' or not raw:
            fail('Bearer token required', 401)
        g.user = users.authenticate(raw)
        if g.user is None:
            fail('Invalid or expired token', 401)
        return view(*args, **kwargs)
    return wrapped
