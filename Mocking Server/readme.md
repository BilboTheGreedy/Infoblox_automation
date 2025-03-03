python.exe .\infoblox_client.py create network --network 192.168.1.0/24 --comment "Test network"

python.exe .\infoblox_client.py create record:a --a_record www.example.com:192.168.1.10 --comment "Website A record"

python.exe .\infoblox_client.py create record:host --host server1.example.com:192.168.1.20 --comment "Application server"

python.exe .\infoblox_client.py get network

python.exe .\infoblox_client.py get network --query "network=192.168.1.0/24"

python.exe .\infoblox_client.py next_ip 10.10.10.0/24

python.exe .\infoblox_client.py search_ip --ip 192.168.1.10

python.exe .\infoblox_client.py search_ip --network 192.168.1.0/24