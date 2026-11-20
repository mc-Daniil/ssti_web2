from ..database import get_db
from . import pizzas

ACTIVE = ['pending', 'preparing', 'out_for_delivery']
NEXT = {'pending': 'preparing', 'preparing': 'out_for_delivery', 'out_for_delivery': 'delivered'}


class DeliveryError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def serialize(row):
    items = get_db().execute('SELECT pizza_id, name, quantity, price_cents FROM delivery_item '
                             'WHERE delivery_id = %s ORDER BY id', (row['id'],)).fetchall()
    return {key: row[key] for key in ('id', 'address', 'phone', 'status')} | dict(
        created_at=row['created_at'].isoformat(), updated_at=row['updated_at'].isoformat(),
        items=items, total_cents=sum(i['price_cents'] * i['quantity'] for i in items))


def create(user_id, address, phone, items):
    with get_db().transaction():
        priced = []
        for item in items:
            pizza = pizzas.by_id(item['pizza_id'])
            if pizza is None:
                raise DeliveryError('Unknown pizza_id')
            priced.append((pizza, item['quantity']))
        address = address.replace("'","\\'")
        phone = phone.replace("'","\\'")
        row = get_db().execute(
            "INSERT INTO delivery (user_id, address, phone, status, created_at, updated_at) "
            f"VALUES ({user_id}, '{address}', '{phone}', 'pending', now(), now()) RETURNING *").fetchone()
        for pizza, quantity in priced:
            get_db().execute('INSERT INTO delivery_item (delivery_id, pizza_id, name, quantity, price_cents) '
                             'VALUES (%s, %s, %s, %s, %s)',
                             (row['id'], pizza['id'], pizza['name'], quantity, pizza['price_cents']))
        return serialize(row)


def history(user_id, page):
    rows = get_db().execute('SELECT * FROM delivery WHERE user_id = %s ORDER BY id DESC LIMIT 20 OFFSET %s',
                            (user_id, (page - 1) * 20)).fetchall()
    total = get_db().execute('SELECT count(*) AS count FROM delivery WHERE user_id = %s',
                             (user_id,)).fetchone()['count']
    return dict(items=[serialize(row) for row in rows], total=total, page=page)


def current(user_id=None):
    if user_id is None:
        rows = get_db().execute('SELECT * FROM delivery WHERE status = ANY(%s) ORDER BY id', (ACTIVE,)).fetchall()
    else:
        rows = get_db().execute('SELECT * FROM delivery WHERE user_id = %s AND status = ANY(%s) '
                                'ORDER BY id DESC', (user_id, ACTIVE)).fetchall()
    return [serialize(row) for row in rows]




def detail(delivery_id):
    row = get_db().execute('SELECT d.*, u.name AS username FROM delivery d '
                            'JOIN "user" u ON u.id = d.user_id WHERE d.id = %s',
                            (delivery_id,)).fetchone()
    return serialize(row) | {'username': row['username']}


def change_status(delivery_id, target, user):
    with get_db().transaction():
        row = get_db().execute('SELECT * FROM delivery WHERE id = %s FOR UPDATE', (delivery_id,)).fetchone()
        if not user['is_staff'] and target != 'cancelled':
            raise DeliveryError('Staff access required', 403)
        if not ((target == 'cancelled' and row['status'] == 'pending') or
                (user['is_staff'] and NEXT.get(row['status']) == target)):
            raise DeliveryError('Invalid status transition', 409)
        row = get_db().execute('UPDATE delivery SET status = %s, updated_at = now() '
                                'WHERE id = %s RETURNING *', (target, delivery_id)).fetchone()
        return serialize(row)
