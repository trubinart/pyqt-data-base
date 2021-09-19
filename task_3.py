from tabulate import tabulate
import ipaddress
import subprocess


def host_ping(list: list):
    table = {
        'reachable': [],
        'unreachable': []
    }

    for item in list:
        host = ipaddress.ip_address(item)

        response = subprocess.call(f'ping -c 1 {host}',
                                   shell=True, stdout=open("/dev/null"))
        if response == 0:
            table['reachable'].append(item)
        else:
            table['unreachable'].append(item)
    return table

def host_range_ping(network: str):
    network = ipaddress.ip_network(network)
    table = host_ping(network)
    print(tabulate(table, headers='keys'))

if __name__ == '__main__':
    host_range_ping('192.168.1.0/24')


