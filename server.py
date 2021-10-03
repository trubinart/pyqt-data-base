import sys
import socket
from utils.moduls import Proto
from services import actions, status_code
from socket import *
import logging.config
from select import *
from utils.descriptors import HostPortDescriptor
from utils.metaclass import DocMeta
from server_db import ServerStorage
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
import threading

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

                        #запись в базу данных
                        self.database.user_login(message['user']['account_name'], client_ip, client_port)
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

                    if message['action'] == 'msg':
                        self.database.write_message_history(message['from'], message['message'])
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

    # Функция обновляющяя список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        main_window.active_clients_table.setModel(
            gui_create_model(database))
        main_window.active_clients_table.resizeColumnsToContents()
        main_window.active_clients_table.resizeRowsToContents()

    # Функция создающяя окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert('/Users/macbookair/Documents/1 - GeekBrains/pyqt-data-base/pyqt-data-base/')
        config_window.db_file.insert('bd_server.db3')
        config_window.port.insert('123')
        config_window.ip.insert('123')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    # Запускаем GUI
    server_app.exec_()


if __name__ == '__main__':
    start_server_with_gui()
    # database = ServerStorage()
    # server = Server(database)
    # server.run()
