import sys
import socket
from utils.moduls import Proto
from services import actions, status_code
from socket import *
import logging.config
from select import *
from utils.descriptors import HostPortDescriptor
from utils.metaclass import DocMeta
from server.db_server import ServerStorage
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from server.server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
import threading
from server.add_user import RegisterUser
import binascii
import os
import hmac
from encryption import _encrypt, _decrypt

new_connection = False
conflag_lock = threading.Lock()


class Server(threading.Thread, Proto, metaclass=DocMeta):
    listen_ip = HostPortDescriptor()
    listen_port = HostPortDescriptor()

    def __init__(self, database):

        self.database = database

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

        # Конструктор предка
        super(Server, self).__init__()

    def create_presence_responce(self, message):
        """:создание ответа сервера на PRESENCE СООБЩЕНИЕ ОТ КЛИЕНТА
         """
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

    def autorize_user(self, sock, message, encoding, client_with_message, client_ip, client_port):
        """:авторизация юзера на сервере"""
        # Проверяем что пользователь зарегистрирован на сервере.

        pub_key = message['user']['publick_key']
        if not self.database.check_user(message['user']['account_name']):
            response = {'response': 400, 'error': 'Пользователь не зарегистрирован.'}
            try:
                self.logger.info(f'Unknown username, sending {response}')
                self.send_message(sock, response, encoding)
            except OSError:
                pass
            sock.close()
        else:
            self.logger.info('Correct username, starting passwd check.')
            # Иначе отвечаем 511 и проводим процедуру авторизации
            # Словарь - заготовка
            message_auth = {'response': 511, 'data': None}
            # Набор байтов в hex представлении
            random_str = binascii.hexlify(os.urandom(64))
            # В словарь байты нельзя, декодируем (json.dumps -> TypeError)
            message_auth['data'] = random_str.decode('ascii')
            # Создаём хэш пароля и связки с рандомной строкой, сохраняем
            # серверную версию ключа
            hash = hmac.new(self.database.get_hash(message['user']['account_name']), random_str, 'MD5')
            digest = hash.digest()
            self.logger.info(f'Auth message = {message_auth}')

            try:
                # Обмен с клиентом
                self.send_message(sock, message_auth, encoding)
                ans = self.get_message(sock, int(self.config['MAX_PACKAGE_LENGTH']), self.config['ENCODING'])
            except OSError as err:
                self.logger.info('Error in auth, data:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(ans['data'])
            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.

            if hmac.compare_digest(digest, client_digest):
                # запись в базу данных
                self.database.user_login(message['user']['account_name'], client_ip, client_port, pub_key)
                self.database.login_history(message['user']['account_name'])

                response = self.create_presence_responce(message)
                try:
                    self.send_message(client_with_message, response, self.config['ENCODING'])
                    self.logger.info(f'Установлено соединение с клиентом {message["user"]}')
                except:
                    # запись в базу данных
                    self.database.user_logout(message['user']['account_name'])
                    self.database.login_history(message['user']['account_name'])

                    self.logger.error(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
            else:
                client_with_message.close()

    def run(self):
        """:старт сервера
         """
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
                client_ip, client_port = client.getpeername()
            except OSError:
                pass
            else:
                self.logger.info(f'Установлено соединение с {client_address}')
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
                        self.autorize_user(client_with_message, message, self.config['ENCODING'], client_with_message,
                                           client_ip, client_port)

                    if message['action'] == 'msg':
                        # keys = self.database.get_keys(message['from']).encode('utf-8')

                        """
                        ключ должен лежать в БД сервера и надо его брать от туда
                        он туда попадает из файла ключа клиента
                        
                        но ключ для расшифровки должен быть в байтах
                        я не понял как передать этот в ключ в бд сервера от клиента в байтах
                        поэтому хардкод
                        """

                        keys = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAkiKjw37konLf75RQAB50Ehc7rynkRdhC+W0HeILOeyrGHZSE\nx1N2H1AGDiuy96rWOzkkAXORK6+VTC6VuZmIZmnWLqrWeKKYOYEhxMbvMaunkuUC\nhsK+4jv1FRkbruKYNq72KABPWNcoEfq5a2e3HE5NFqDzHseqeFAEMYJI7sS+yye1\npvCkuaUXtrzTNrLYkvuGx6ZcmhfMh/evMv0BmXb7WuHKU652njRT0gBDnyY4GDNJ\nnkK4OEMsOGZLBYRrMo+67Zb08ND9QLtE2oMRqmqD+GGFH0nGYYSEVW+WRIKHneZM\nk6wUW+nC7EvCLJXDqy49pwkHW7EPF8Dp4Hw/6wIDAQABAoIBADhm6zsEil0SplCz\nNw9csaLb2brZGdRFTFA1nxkJr4UFNNLs5DSEh4Y9XiDxB9GkW6we+UEgKCsqyR5O\nqpYoZmdUuQhpAn8sDkG/j9eBiodqv7In9ooptv/dcVHTz4X3yhTtAW/d8sIQxNPv\np8oHDTr9E67EryE1ohtukrfDF8AjlT17zcuvyrxd6MirCTEFEjSn8KG0lnynES1p\nw+9ywwLgqGvN2aGgJG75lnHz9ap7x5Hp7Jw2C7V7D3Cc1rTfKS8ktMIymHv/9Nqi\n70x73ruzNf8rnO8GfVHPQuZk/jxohYUuWLSPedxiShIfPqmQl4cpP0qUQW/oEcRV\nd7gebDECgYEAvCYveYaxYVESxTqaWz9VHJL5utNLku9IzsX1DSMyimwlRCqjRrCQ\nAvdpn0c4j3kjeJBIM6wAyAbjGkewo0jbh6e+eo7gykrrO3h9J9KZ8hUaOCINc+ht\n39dW1gwpgDlAq5tJmfUxrDTGF145nmgWytA8HfIP7ycJJUw2U9ni+7ECgYEAxtXC\n8OsnE1Ac/ZIftQJZfx2+1bBxJxmMr8rqyj/GzBLhzAhXHQhyBgMQDwV9jC1S1Anq\nKNCs3XWEB65ddaRcb5h2GDd9cBNasu8frQKI6HMZ1uNFkXQI6MIcL1b5LARl2DUy\ndL3XMebhiU/tFGF/PUYyrLYbJ+bATCo6nb3zSFsCgYEAuSHBuQyF4UIK/DKry3lH\n4DPmsqRSSqRUudEjTOgDRR0gljB2NIprSd/0+Br2VoZWFr2xrdZjdm8Aa816y1BX\nYuX1kVahbavGRuBKFjMt83w8LlujbReZdZXIBho1g8vSDIliJLGVTOMov7mhbHLz\namD3pmeWsjVw1FhnZJ6SsCECgYA5TUtz8OD/ANyJ+z2mBbpTFvhzTvkdIpDX7KvD\ng6PAFkT6bwDj/hYWQ3WyTovDBSDUuNLB1nmrDP3y1L5cc/SruI14Jy3ASeOeo6lG\nS++2xc0Rj8fxxjX3FlHXFsKSe+X57ELRQBCvcfFXiDAz6nEn8H4UJhsnYanTiWwB\nH8fn9wKBgQCWpuJiCwnIa04086l4m0lSqngNS/URqNQIahR88BkZxOIUcY5C8/4u\nZ1N2jvgKifEz6u4bxHzzqaIfLwl9ThYfyl5LdfJSgPlHFJniasyfZ+B1dmmVwRQA\nYXKQtM7W7+EzOEBTwWtCqz+7dIOcBXr6Q7p+ZMshenOOlarDS78Z9Q==\n-----END RSA PRIVATE KEY-----'
                        text_str = message['message']
                        print(f'получил - {text_str}')

                        text_bytes = binascii.unhexlify(text_str)
                        print(f'байты - {text_bytes}')
                        print(f'ключ - {self.database.get_keys(message["from"]).encode("utf-8")}')
                        decrypt_message = _decrypt(text_bytes, keys)

                        self.database.write_message_history(message['from'], decrypt_message)
                        message['message'] = decrypt_message
                        messages_list.append(message)
                        self.logger.info(f'Сообщение от {message["from"]} добавлен в лист рассылки')

            if messages_list and send_data_lst:
                for msg in messages_list:
                    for waiting_client in send_data_lst:
                        try:
                            self.send_message(waiting_client, msg, self.config['ENCODING'])
                            self.logger.info(f'Сообщение к {waiting_client} отправлено')
                        except:
                            # запись в базу данных
                            self.database.user_logout(message['user']['account_name'])
                            self.database.login_history(message['user']['account_name'])

                            self.logger.error(f'Клиент {waiting_client.getpeername()} отключился от сервера.')

                    messages_list.remove(msg)
                    self.logger.info(f'Сообщение {msg} всем отправлено')


def start_server_with_gui():
    """"
    создание сервера в gui интерфейсом
    """
    # Создание экземпляра класса - сервера и его запуск:
    database = ServerStorage()
    server = Server(database)
    server.daemon = True
    server.start()

    # Создаём графическое окружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()


    def list_update():
        '''
        Функция обновляющяя список подключённых, проверяет флаг подключения,
        и если надо обновляет список
        '''
        main_window.active_clients_table.setModel(
            gui_create_model(database))
        main_window.active_clients_table.resizeColumnsToContents()
        main_window.active_clients_table.resizeRowsToContents()


    def show_statistics():
        '''
        Функция создающяя окно со статистикой клиентов
        '''
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()


    def server_config():
        '''Функция создающая окно с настройками сервера.
        '''
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert('/Users/macbookair/Documents/1 - GeekBrains/pyqt-data-base/pyqt-data-base/')
        config_window.db_file.insert('bd_server.db3')
        config_window.port.insert('123')
        config_window.ip.insert('123')

    def reg_user():
        '''Метод создающий окно регистрации пользователя.'''
        global reg_window
        reg_window = RegisterUser(database, server)
        reg_window.show()

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)
    main_window.register_btn.triggered.connect(reg_user)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    start_server_with_gui()
    # database = ServerStorage()
    # server = Server(database)
    # server.run()
