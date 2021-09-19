import ipaddress
import subprocess


def host_ping(list: list):

    for item in list:
        host = ipaddress.ip_address(item)

        response = subprocess.call(f'ping -c 1 {host}',
                                   shell=True, stdout=open("/dev/null"))
        if response == 0:
            print(f'IP {host} active')
        else:
            print(f'IP {host} NOT active')

def host_range_ping(network: str):
    network = list(ipaddress.ip_network(network))
    host_ping(network)

if __name__ == '__main__':
    host_range_ping('192.168.1.0/24')

