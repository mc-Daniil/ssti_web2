from pathlib import Path
from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_file
from ..database import get_db
bp = Blueprint('web', __name__)


@bp.get('/')
def index():
    return render_template('index.html')


@bp.get('/image')
def image():
    filename = request.args.get('filename', '')
    if not filename or '\x00' in filename:
        abort(400, description='Image filename required')
    path = Path(current_app.static_folder) / 'images' / filename
    try:
        return send_file(path)
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        abort(404, description='Image not found')


@bp.get('/health')
def health():
    get_db().execute('SELECT 1')
    return jsonify(status='ok')
