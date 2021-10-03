import subprocess

class HostPortDescriptor:

    def __set__(self, instance, value):
        if self.new_attr == 'listen_ip':
            proc = subprocess.call(f'ping -W 500 -c 1 {value}',
                                   shell=True, stdout=open("/dev/null"))
            if proc == 0:
                instance.logger.info(f'Успешное подключение: {value}')
                instance.__dict__[self.new_attr] = value
            else:
                instance.logger.error(f'Указан не доступный listen_ip', exc_info=True)
                raise ValueError('Указан не доступный listen_ip')

        if self.new_attr == 'listen_port':
            if not 65535 >= int(value) >= 1024:
                instance.logger.error(f'Порт должен быть указан в пределах от 1024 до 65535', exc_info=True)
                raise ValueError('Порт должен быть указан в пределах от 1024 до 65535')
            else:
                instance.__dict__[self.new_attr] = value
                instance.logger.info(f'Успешное подключение на порту: {value}')

    def __set_name__(self, owner, name):
        self.new_attr = name