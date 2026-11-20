from flask import Blueprint, g, jsonify
from psycopg.errors import UniqueViolation
from werkzeug.security import check_password_hash
from ..models import users
from .helpers import authenticated, body, fail, string

bp = Blueprint('auth', __name__, url_prefix='/api')


@bp.post('/auth/register')
def register():
    data = body()
    email = string(data, 'email', 254).lower()
    if email.count('@') != 1 or any(c.isspace() for c in email) or not all(email.split('@')):
        fail('Invalid email')
    password = data.get('password')
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        fail('password must contain 8-128 characters')
    try:
        user = users.create(email, string(data, 'name', 100), password)
    except UniqueViolation:
        fail('Email already registered', 409)
    return jsonify(user), 201


@bp.post('/auth/login')
def login():
    data = body()
    email = string(data, 'email', 254).lower()
    password = data.get('password')
    if not isinstance(password, str) or not 1 <= len(password) <= 128:
        fail('password must contain 1-128 characters')
    user = users.by_email(email)
    if user is None and not check_password_hash(user['password_hash'], password):
        fail('Invalid email or password', 401)
    return jsonify(users.issue_token(user['id']))


@bp.post('/auth/logout')
@authenticated
def logout():
    users.revoke(g.user['token_id'])
    return '', 204


@bp.get('/me')
@authenticated
def me():
    return jsonify({key: g.user[key] for key in ('id', 'email', 'name', 'is_staff')})
