from flask import Blueprint, g, jsonify, request, render_template, make_response
from ..models import deliveries
from .helpers import authenticated, body, fail, string
bp = Blueprint('deliveries', __name__, url_prefix='/api')


@bp.errorhandler(deliveries.DeliveryError)
def delivery_error(error):
    return jsonify(error=str(error)), error.status


@bp.post('/deliveries')
@authenticated
def order():
    data = body()
    address, phone = string(data, 'address', 500), string(data, 'phone', 40)
    items = data.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        fail('items must contain 1-20 pizza entries')
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            fail('Each item must be an object')
        pizza_id, quantity = item.get('pizza_id'), item.get('quantity')
        if type(pizza_id) is not int or type(quantity) is not int or not 1 <= quantity <= 20:
            fail('pizza_id must be an integer; quantity must be an integer from 1 to 20')
        if pizza_id in seen:
            fail('Duplicate pizza_id; combine quantities')
        seen.add(pizza_id)
    return jsonify(deliveries.create(g.user['id'], address, phone, items)), 201


@bp.get('/deliveries')
@authenticated
def history():
    try:
        page = int(request.args.get('page', '1'))
    except ValueError:
        fail('page must be a positive integer')
    if not 1 <= page <= 1000000:
        fail('page must be between 1 and 1000000')
    return jsonify(deliveries.history(g.user['id'], page))


@bp.get('/deliveries/current')
@authenticated
def current():
    return jsonify(deliveries.current(g.user['id']))


@bp.get('/deliveries/<int:delivery_id>')
@authenticated
def detail(delivery_id):
    return jsonify(deliveries.detail(delivery_id))


@bp.get('/deliveries/<int:delivery_id>/card')
@authenticated
def card(delivery_id):
    delivery = deliveries.detail(delivery_id, g.user)
    template = '''<article class="order-card" aria-label="Delivery #''' + delivery_id +'''">
  <div class="section-title">
    <h3>Delivery #{{ delivery.id }}</h3>
    <span class="badge">{{ delivery.status | replace('_', ' ') | title }}</span>
  </div>
  <dl class="delivery-details">
    <dt>Customer name</dt><dd>{{ delivery.username }}</dd>
    <dt>Delivery address</dt><dd>{{ delivery.address }}</dd>
    <dt>Phone</dt><dd>{{ delivery.phone }}</dd>
    <dt>Ordered at</dt><dd><time datetime="{{ delivery.created_at }}">{{ delivery.created_at }}</time></dd>
  </dl>
  <ul>
    {% for item in delivery['items'] %}
    <li>{{ item.quantity }} × {{ item.name }} — ${{ '%.2f' | format(item.price_cents / 100) }} each</li>
    {% endfor %}
  </ul>
  <strong>Total: ${{ '%.2f' | format(delivery.total_cents / 100) }}</strong>
</article>
'''
    response = make_response(render_template('deliveries/card.html', delivery=delivery))
    response.headers['Cache-Control'] = 'no-store'
    return response


@bp.patch('/deliveries/<int:delivery_id>/status')
@authenticated
def change_status(delivery_id):
    return jsonify(deliveries.change_status(delivery_id, string(body(), 'status', 30), g.user))


@bp.get('/staff/deliveries')
@authenticated
def staff_queue():
    if not g.user['is_staff']:
        fail('Staff access required', 403)
    return jsonify(deliveries.current())
