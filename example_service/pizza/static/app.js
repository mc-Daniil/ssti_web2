'use strict';
const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem('pizza-token'), user = null, menu = [], cart = new Map();
let registering = false, historyPage = 1, refreshing = false;
const money = (cents) => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(cents / 100);
const labels = {pending: 'Order received', preparing: 'In the oven', out_for_delivery: 'On the way', delivered: 'Delivered', cancelled: 'Cancelled'};
const nextStatus = {pending: 'preparing', preparing: 'out_for_delivery', out_for_delivery: 'delivered'};
function node(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
function notify(text, error = false) { $('notice').textContent = text; $('notice').classList.toggle('error', error); $('notice').hidden = false; }
function button(text, handler, className = 'outline') { const b = node('button', text, className); b.type = 'button'; b.onclick = async () => { b.disabled = true; try { await handler(); } catch (e) { notify(e.message, true); } finally { b.disabled = false; } }; return b; }
async function api(path, method = 'GET', data) {
  const headers = {}; if (token) headers.Authorization = `Bearer ${token}`;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api${path}`, {method, headers, body: data === undefined ? undefined : JSON.stringify(data)});
  if (response.status === 204) return null;
  const result = await response.json();
  if (!response.ok) { if (response.status === 401 && user) clearSession(); throw new Error(result.error || 'Something went wrong. Please try again.'); }
  return result;
}
function updateAccount() {
  $('account-button').textContent = user ? user.name : 'Sign in';
  $('logout').hidden = !user; $('history-panel').hidden = !user; $('staff-panel').hidden = !user?.is_staff;
  $('orders-hint').textContent = user ? 'Updates automatically every 15 seconds.' : 'Sign in to see your deliveries.';
}
function clearSession() { token = null; user = null; sessionStorage.removeItem('pizza-token'); updateAccount(); $('current-orders').replaceChildren(); $('history').replaceChildren(); $('staff-orders').replaceChildren(); $('delivery-result').replaceChildren(); }
async function lookupDelivery(id) {
  $('delivery-result').replaceChildren();
  if (!user) { showAuth(); return; }
  const requestToken = token;
  const response = await fetch(`/api/deliveries/${id}/card`, {headers: {Authorization: `Bearer ${requestToken}`}});
  if (requestToken !== token) return;
  if (!response.ok) {
    const error = await response.json();
    if (response.status === 401) clearSession();
    throw new Error(error.error || 'Unable to find delivery');
  }
  const html = await response.text();
  if (requestToken !== token) return;
  // This same-origin HTML is rendered by Jinja with automatic escaping enabled.
  $('delivery-result').innerHTML = html;
  $('delivery-result').scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
$('delivery-lookup').onsubmit = async (event) => {
  event.preventDefault(); const submit = event.target.querySelector('button'); submit.disabled = true;
  try { await lookupDelivery($('delivery-id').value); }
  catch (e) { $('delivery-result').textContent = e.message; }
  finally { submit.disabled = false; }
};
function showAuth() { $('auth-error').textContent = ''; $('auth-dialog').showModal(); }
$('account-button').onclick = () => user ? notify(`Signed in as ${user.email}`) : showAuth();
$('close-auth').onclick = () => $('auth-dialog').close();
$('toggle-auth').onclick = () => {
  registering = !registering; $('name-field').hidden = !registering;
  $('auth-form').elements.name.required = registering;
  $('auth-form').elements.password.minLength = registering ? 8 : 1;
  $('auth-form').elements.password.autocomplete = registering ? 'new-password' : 'current-password';
  $('auth-title').textContent = registering ? 'Join the pizza club' : 'Welcome back';
  $('auth-submit').textContent = registering ? 'Create account' : 'Sign in';
  $('toggle-auth').textContent = registering ? 'Already a member? Sign in' : 'New here? Create an account';
  $('auth-error').textContent = '';
};
$('auth-form').onsubmit = async (event) => {
  event.preventDefault(); $('auth-submit').disabled = true; $('auth-error').textContent = '';
  const data = Object.fromEntries(new FormData(event.target));
  try {
    if (registering) await api('/auth/register', 'POST', data);
    const session = await api('/auth/login', 'POST', data); token = session.access_token; sessionStorage.setItem('pizza-token', token);
    user = await api('/me'); updateAccount(); $('auth-dialog').close(); event.target.reset(); historyPage = 1;
    notify(`Welcome, ${user.name}. Your table is wherever you are.`); await refreshOrders();
  } catch (e) { $('auth-error').textContent = e.message; } finally { $('auth-submit').disabled = false; }
};
$('logout').onclick = async () => { try { await api('/auth/logout', 'POST'); clearSession(); cart.clear(); renderCart(); $('checkout').reset(); notify('You have signed out.'); } catch (e) { notify(e.message, true); } };
function renderMenu() {
  $('menu-list').replaceChildren();
  const descriptions = {Margherita: 'Tomato, mozzarella, and a timeless love of the classics.', Pepperoni: 'A bold favorite, with pepperoni and melted mozzarella.', Vegetarian: 'A colorful mix of vegetables on a cheesy tomato base.'};
  menu.forEach(pizza => {
    const card = node('article', undefined, 'pizza-card'), icon = node('img', undefined, 'pizza-photo');
    const photos = {Margherita: 'margherita', Pepperoni: 'pepperoni', Vegetarian: 'vegetarian'};
    icon.src = `/image?filename=${encodeURIComponent((photos[pizza.name] || 'hero') + '.jpg')}`; icon.alt = `${pizza.name} pizza`;
    icon.loading = 'lazy'; icon.width = 150; icon.height = 130;
    const description = node('div', undefined, 'description'); description.append(node('h3', pizza.name), node('p', descriptions[pizza.name] || 'Fresh from our kitchen.'), node('strong', money(pizza.price_cents)));
    card.append(icon, description, button('Add to basket', () => { const count = cart.get(pizza.id) || 0; if (count >= 20) throw new Error('Maximum 20 of each pizza.'); cart.set(pizza.id, count + 1); renderCart(); }, 'primary'));
    $('menu-list').append(card);
  });
}
function renderCart() {
  $('cart').replaceChildren(); let total = 0, count = 0;
  if (!cart.size) $('cart').append(node('p', 'Your pizza night is waiting. Add a favorite from the menu.', 'muted'));
  cart.forEach((quantity, id) => {
    const pizza = menu.find(p => p.id === id); total += quantity * pizza.price_cents; count += quantity;
    const row = node('div', undefined, 'cart-row'), controls = node('div', undefined, 'quantity');
    const minus = button('−', () => { quantity > 1 ? cart.set(id, quantity - 1) : cart.delete(id); renderCart(); }); minus.setAttribute('aria-label', `Remove one ${pizza.name}`);
    const plus = button('+', () => { if (quantity < 20) cart.set(id, quantity + 1); renderCart(); }); plus.setAttribute('aria-label', `Add one ${pizza.name}`); plus.disabled = quantity >= 20;
    controls.append(minus, node('span', String(quantity)), plus); row.append(node('span', pizza.name), controls); $('cart').append(row);
  });
  $('total').textContent = money(total); $('basket-count').textContent = `${count} items`; $('place-order').disabled = !count;
}
$('checkout').onsubmit = async (event) => {
  event.preventDefault(); if (!user) { showAuth(); return; } if (!cart.size) return;
  $('place-order').disabled = true;
  try {
    const data = Object.fromEntries(new FormData(event.target)); data.items = [...cart].map(([pizza_id, quantity]) => ({pizza_id, quantity}));
    const delivery = await api('/deliveries', 'POST', data); cart.clear(); renderCart(); historyPage = 1;
    notify(`Order #${delivery.id} received. Follow its progress below.`); await refreshOrders(); $('orders').scrollIntoView({behavior: 'smooth'});
  } catch (e) { notify(e.message, true); } finally { $('place-order').disabled = !cart.size; }
};
function orderCard(order, staff = false) {
  const card = node('article', undefined, 'order-card'), heading = node('div', undefined, 'section-title');
  heading.append(node('h3', `Order #${order.id}`), node('span', labels[order.status] || order.status, 'badge'));
  card.append(heading);
  if (order.status !== 'cancelled') {
    const progress = node('div', undefined, 'progress'); progress.setAttribute('aria-hidden', 'true');
    const step = ['pending', 'preparing', 'out_for_delivery', 'delivered'].indexOf(order.status);
    for (let i = 0; i < 4; i++) progress.append(node('span', undefined, i <= step ? 'done' : ''));
    card.append(progress);
  }
  card.append(node('p', order.items.map(i => `${i.quantity} × ${i.name}`).join(' · ')), node('p', `${order.address} · ${order.phone}`), node('p', new Date(order.created_at).toLocaleString(), 'small'), node('strong', money(order.total_cents)));
  const actions = node('div', undefined, 'order-actions');
  actions.append(button('View details', async () => { $('delivery-id').value = order.id; await lookupDelivery(order.id); }));
  async function change(status) { await api(`/deliveries/${order.id}/status`, 'PATCH', {status}); notify(`Order #${order.id}: ${labels[status]}.`); await refreshOrders(); }
  if (order.status === 'pending') actions.append(button('Cancel order', () => change('cancelled')));
  if (staff && nextStatus[order.status]) actions.append(button(`Mark: ${labels[nextStatus[order.status]]}`, () => change(nextStatus[order.status]), 'primary'));
  if (actions.childElementCount) { actions.style.marginTop = '20px'; card.append(actions); }
  return card;
}
function showOrders(id, orders, staff = false) { $(id).replaceChildren(...(orders.length ? orders.map(order => orderCard(order, staff)) : [node('p', staff ? 'The queue is clear.' : 'No deliveries here yet.', 'muted')])); }
async function refreshOrders() {
  if (!user || refreshing) return; refreshing = true;
  try {
    const [current, history] = await Promise.all([api('/deliveries/current'), api(`/deliveries?page=${historyPage}`)]);
    if (!user) return;
    showOrders('current-orders', current); showOrders('history', history.items);
    $('page-label').textContent = `Page ${historyPage} · ${history.total} orders`; $('previous').disabled = historyPage <= 1; $('next').disabled = historyPage * 20 >= history.total;
    if (user.is_staff) showOrders('staff-orders', await api('/staff/deliveries'), true);
  } catch (e) { notify(e.message, true); } finally { refreshing = false; }
}
$('refresh').onclick = refreshOrders;
$('previous').onclick = () => { if (!refreshing && historyPage > 1) { historyPage--; refreshOrders(); } };
$('next').onclick = () => { if (!refreshing) { historyPage++; refreshOrders(); } };
async function start() {
  try { menu = await api('/pizzas'); renderMenu(); } catch (e) { $('menu-list').textContent = 'Menu unavailable. Please reload to try again.'; notify(e.message, true); }
  renderCart();
  if (token) { try { user = await api('/me'); } catch (e) { clearSession(); notify('Please sign in again to view your deliveries.'); } }
  updateAccount(); await refreshOrders();
}
start(); setInterval(() => { if (!document.hidden) refreshOrders(); }, 15000);
