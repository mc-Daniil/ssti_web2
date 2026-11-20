"""Request-scoped direct psycopg connections with explicit write transactions."""
from pathlib import Path
import click
import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def get_db():
    if 'db' not in g:
        g.db = psycopg.connect(current_app.config['DATABASE_URL'], row_factory=dict_row, autocommit=True)
    return g.db


def close_db(error=None):
    connection = g.pop('db', None)
    if connection is not None:
        connection.close()


def initialize():
    with get_db().transaction():
        get_db().execute(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        for name, price in [('Margherita', 900), ('Pepperoni', 1200), ('Vegetarian', 1100)]:
            get_db().execute('INSERT INTO pizza (name, price_cents) VALUES (%s, %s) '
                             'ON CONFLICT (name) DO NOTHING', (name, price))


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command('init-db')
    def init_db_command():
        initialize()
        click.echo('Database initialized')

    @app.cli.command('promote-staff')
    @click.argument('email')
    def promote_staff(email):
        from .models.users import promote
        if not promote(email.strip().lower()):
            raise click.ClickException('Register this user first')
        click.echo('Staff access granted')
