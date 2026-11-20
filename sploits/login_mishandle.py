from service_lib import ServiceClient
from sys import argv
URL = argv[1]      # Serviceaddr
email = argv[2]    # email from attack_data

client = ServiceClient(URL)

client.login(email, '123')

print(client.get_deliveries())