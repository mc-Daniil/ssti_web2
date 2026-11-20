from ..database import get_db


def all_pizzas():
    return get_db().execute('SELECT id, name, price_cents FROM pizza ORDER BY id').fetchall()


def by_id(pizza_id):
    return get_db().execute('SELECT * FROM pizza WHERE id = %s', (pizza_id,)).fetchone()
