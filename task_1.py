import subprocess
import ipaddress

def host_ping(list: list):
    for item in list:
        host = ipaddress.ip_address(item)

        response = subprocess.call(f'ping -c 1 {host}',
                                   shell=True, stdout=open("/dev/null"))
        if response == 0:
            print(f'IP {host} active')
        else:
            print(f'IP {host} NOT active')

if __name__ == '__main__':
    list_ip_adress = ['192.168.1.254', '192.168.1.154']
    host_ping(list_ip_adress)

