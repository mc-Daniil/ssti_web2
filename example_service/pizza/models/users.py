import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from werkzeug.security import generate_password_hash
from ..database import get_db


def create(email, name, password):
    return get_db().execute(
        'INSERT INTO "user" (email, name, password_hash, is_staff) VALUES (%s, %s, %s, FALSE) '
        'RETURNING id, email, name', (email, name, generate_password_hash(password))).fetchone()


def by_email(email):
    return get_db().execute('SELECT * FROM "user" WHERE email = %s', (email,)).fetchone()


def promote(email):
    return get_db().execute('UPDATE "user" SET is_staff = TRUE WHERE email = %s', (email,)).rowcount


def issue_token(user_id):
    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    get_db().execute('INSERT INTO token (digest, user_id, expires_at) VALUES (%s, %s, %s)',
                     (sha256(raw.encode()).hexdigest(), user_id, expires))
    return dict(access_token=raw, token_type='Bearer', expires_at=expires.isoformat())


def authenticate(raw):
    return get_db().execute(
        'SELECT u.id, u.name, u.email, u.is_staff, t.id AS token_id '
        'FROM "user" u JOIN token t ON t.user_id = u.id '
        'WHERE t.digest = %s AND t.expires_at > now()',
        (sha256(raw.encode()).hexdigest(),)).fetchone()


def revoke(token_id):
    get_db().execute('DELETE FROM token WHERE id = %s', (token_id,))
