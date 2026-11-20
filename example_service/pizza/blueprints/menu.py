from flask import Blueprint, jsonify
from ..models.pizzas import all_pizzas
bp = Blueprint('menu', __name__)


@bp.get('/api/pizzas')
def menu():
    return jsonify(all_pizzas())
