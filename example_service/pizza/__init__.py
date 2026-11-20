import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from . import database
from .blueprints import auth, deliveries, menu, web


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(DATABASE_URL=os.getenv('DATABASE_URL', 'postgresql://pizza:pizza@localhost:5432/pizza'),
                      MAX_CONTENT_LENGTH=32 * 1024)
    if config:
        app.config.update(config)
    database.init_app(app)
    for blueprint in (auth.bp, deliveries.bp, menu.bp, web.bp):
        app.register_blueprint(blueprint)

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    return app
