
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ServiceError(Exception):
    """HTTP/transport failure with the original response available for inspection."""

    def __init__(self, message, *, status_code=None, body=b''):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Keep credentials on the configured service; expose redirects as errors.
        return None


class ServiceClient:
    def __init__(self, base_url='http://127.0.0.1:8000', *, timeout=10, token=None):
        if '://' not in base_url:
            base_url = 'http://' + base_url
        parts = urlsplit(base_url)
        if (parts.scheme not in ('http', 'https') or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment):
            raise ValueError('base_url must be an HTTP(S) URL without credentials, query, or fragment')
        if timeout <= 0:
            raise ValueError('timeout must be positive')
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.token = token
        self._opener = build_opener(_NoRedirects())

    def request(self, method, path, *, data=None, params=None, response_type='json'):
        """Request a service-relative path; response_type is json, text, or bytes."""
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('path must start with a single slash')
        if response_type not in ('json', 'text', 'bytes'):
            raise ValueError('response_type must be json, text, or bytes')
        url = self.base_url + path
        if params:
            url += ('&' if '?' in url else '?') + urlencode(params, doseq=True)
        headers = {'Accept': 'application/json' if response_type == 'json' else '*/*'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        payload = None
        if data is not None:
            payload = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = Request(url, data=payload, headers=headers, method=method.upper())
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read()
                status = response.status
                charset = response.headers.get_content_charset() or 'utf-8'
        except HTTPError as error:
            with error:
                raw = error.read()
            try:
                decoded = json.loads(raw)
                message = decoded.get('error', error.reason) if isinstance(decoded, dict) else error.reason
            except (ValueError, UnicodeError):
                message = error.reason
            raise ServiceError(f'HTTP {error.code}: {message}', status_code=error.code, body=raw) from error
        except (URLError, OSError) as error:
            raise ServiceError(f'Request failed: {error}') from error
        if response_type == 'bytes':
            return raw
        if response_type == 'text':
            return raw.decode(charset, errors='replace')
        if status == 204 or not raw:
            return None
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise ServiceError('Expected a JSON response', status_code=status, body=raw) from error

    def register(self, email, password, name):
        return self.request('POST', '/api/auth/register',
                            data={'email': email, 'password': password, 'name': name})

    def login(self, email, password):
        # A failed attempt must not leave the previous user's token active.
        self.token = None
        result = self.request('POST', '/api/auth/login', data={'email': email, 'password': password})
        self.token = result['access_token']
        return result

    def logout(self):
        try:
            return self.request('POST', '/api/auth/logout')
        finally:
            self.token = None

    def get_me(self):
        return self.request('GET', '/api/me')

    def health(self):
        return self.request('GET', '/health')

    def get_homepage(self):
        return self.request('GET', '/', response_type='text')

    def get_pizzas(self):
        return self.request('GET', '/api/pizzas')

    def create_delivery(self, address, phone, items):
        return self.request('POST', '/api/deliveries',
                            data={'address': address, 'phone': phone, 'items': items})

    def get_deliveries(self, page=1):
        return self.request('GET', '/api/deliveries', params={'page': page})

    def get_current_deliveries(self):
        return self.request('GET', '/api/deliveries/current')

    @staticmethod
    def _delivery_path(delivery_id):
        if type(delivery_id) is not int or delivery_id <= 0:
            raise ValueError('delivery_id must be a positive integer')
        return f'/api/deliveries/{delivery_id}'

    def get_delivery(self, delivery_id):
        return self.request('GET', self._delivery_path(delivery_id))

    def get_delivery_card(self, delivery_id):
        return self.request('GET', self._delivery_path(delivery_id) + '/card', response_type='text')

    def update_delivery_status(self, delivery_id, status):
        return self.request('PATCH', self._delivery_path(delivery_id) + '/status', data={'status': status})

    def cancel_delivery(self, delivery_id):
        return self.update_delivery_status(delivery_id, 'cancelled')

    def get_staff_deliveries(self):
        return self.request('GET', '/api/staff/deliveries')

    def get_image(self, filename):
        return self.request('GET', '/image', params={'filename': filename}, response_type='bytes')
