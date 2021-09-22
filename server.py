import sys
import socket
from moduls import Proto
from services import actions, status_code
from socket import *
import logging.config
from select import *
import subprocess


class ServerDescriptor:

    def __set__(self, instance, value):

        if self.new_attr == 'listen_ip':
            proc = subprocess.call(f'ping -W 500 -c 1 {value}',
                                   shell=True, stdout=open("/dev/null"))
            if proc == 0:
                instance.logger.info(f'Успешное подключение на сервере: {value}')
                instance.__dict__[self.new_attr] = value
            else:
                instance.logger.error(f'Указан не доступный listen_ip', exc_info=True)
                raise ValueError('Указан не доступный listen_ip')

        if self.new_attr == 'listen_port':
            if not 65535 >= value >= 1024:
                instance.logger.error(f'Порт должен быть указан в пределах от 1024 до 65535', exc_info=True)
                raise ValueError('Порт должен быть указан в пределах от 1024 до 65535')
            else:
                instance.__dict__[self.new_attr] = value
                instance.logger.info(f'Успешное подключение на порту: {value}')

    def __set_name__(self, owner, name):
        self.new_attr = name


class Server(Proto):
    listen_ip = ServerDescriptor()
    listen_port = ServerDescriptor()

    def __init__(self):
        # НАСТРОЙКИ ЛОГИРОВАНИЯ
        logging.config.fileConfig('log/logging.ini',
                                  disable_existing_loggers=False,
                                  defaults={'logfilename': 'log/server.log'})
        self.logger = logging.getLogger('server')

        # ЗАГРУЖАЮ КОНФИГИ
        self.config = self.load_settings()

        # БЕРУ ПОРТ И IP
        try:
            self.listen_ip = sys.argv[1]
        except IndexError:
            self.logger.error(f'listen_ip сервера передан не верно. '
                              f'Были использованы аргументы из файла settings.ini')
            self.listen_ip = self.config['DEFAULT_IP_ADDRESS']

        try:
            self.listen_port = sys.argv[2]
        except IndexError:
            self.logger.error(f'listen_port сервера передан не верно. '
                              f'Были использованы аргументы из файла settings.ini')
            self.listen_port = int(self.config['DEFAULT_PORT'])

    # СОЗДАЮ ОТВЕТ НА PRESENCE СООБЩЕНИЕ ОТ КЛИЕНТА
    def create_presence_responce(self, message):
        if self.config['ACTION'] in message \
                and message[self.config['ACTION']] == actions.PRESENCE \
                and self.config['TIME'] in message \
                and self.config['USER'] in message:
            self.logger.info(f'Ответ от сервера сформирован успешно - КОД 200')
            return {self.config['RESPONSE']: status_code.OK}

        self.logger.error(f'Некорректное сообщение от клиента. Ответ от сервера: КОД 400 \n'
                          f'{message}')
        return {
            self.config['RESPONSE']: status_code.BAD_REQUEST,
            self.config['ERROR']: 'Bad Request'
        }

    def start_server(self):
        transport = socket(AF_INET, SOCK_STREAM)
        transport.bind((self.listen_ip, self.listen_port))
        transport.listen(int(self.config['MAX_CONNECTIONS']))
        transport.settimeout(0.2)

        self.logger.info(f'Успешное подключение на сервере: host {self.listen_ip}, port {self.listen_port}')

        all_clients = []
        print(f'Запущен сервер ->  {self.listen_ip}: {self.listen_port}')
        while True:
            try:
                client, client_address = transport.accept()
            except OSError:
                pass
            else:
                self.logger.info(f'Установлено соедение с {client_address}')
                all_clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            messages_list = []

            try:
                if all_clients:
                    recv_data_lst, send_data_lst, err_lst = select(all_clients, all_clients, [], 0)
            except OSError:
                pass

            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    message = self.get_message(client_with_message, int(self.config['MAX_PACKAGE_LENGTH']),
                                               self.config['ENCODING'])
                    self.logger.info(f'Сообщение от клиента декодировано успешно')

                    if message['action'] == 'presence':
                        response = self.create_presence_responce(message)
                        try:
                            self.send_message(client_with_message, response, self.config['ENCODING'])
                            self.logger.info(f'Установлено соединение с клиентом {message["user"]}')
                        except:
                            self.logger.error(f'Клиент {client_with_message.getpeername()} отключился от сервера.')

                    if message['action'] == 'msg':
                        messages_list.append(message)
                        self.logger.info(f'Сообщение от {message["from"]} добавлен в лист рассылки')

            if messages_list and send_data_lst:
                for msg in messages_list:
                    for waiting_client in send_data_lst:
                        self.send_message(waiting_client, msg, self.config['ENCODING'])
                        self.logger.info(f'Сообщение к {waiting_client} отправлено')
                    messages_list.remove(msg)
                    self.logger.info(f'Сообщение {msg} всем отправлено')


if __name__ == '__main__':
    server = Server()
    server.start_server()
