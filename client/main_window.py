from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, QEvent, Qt
import sys
import json
import logging
from operator import itemgetter

sys.path.append('../')
from client.main_window_conv import Ui_MainClientWindow

from client.errors import ServerError

logger = logging.getLogger('client')


# Класс основного окна
class ClientMainWindow(QMainWindow):
    def __init__(self, database, client):
        super().__init__()
        # основные переменные
        self.database = database
        self.client = client

        # Загружаем конфигурацию окна из дизайнера
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # Кнопка "Выход"
        self.ui.menu_exit.triggered.connect(qApp.exit)

        # Кнопка отправить сообщение
        self.ui.btn_send.clicked.connect(self.send_message)

        # Дополнительные требующиеся атрибуты
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.history_list_update()
        self.ui.list_messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)

        self.show()


    # Заполняем историю сообщений.
    def history_list_update(self):
        # Получаем историю сортированную по дате
        list = sorted(self.database.get_history(), key= itemgetter(3) )

    # Если модель не создана, создадим.
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)

        # Очистим от старых записей
        self.history_model.clear()
        # Берём не более 20 последних записей.
        length = len(list)
        start_index = 0
        if length > 20:
            start_index = length - 20

        for i in range(start_index, length):
            item = list[i]
            mess = QStandardItem(f'Сообщение от {item[3].replace(microsecond=0)}:\n {item[2]}')
            mess.setEditable(False)
            mess.setBackground(QBrush(QColor(255, 213, 213)))
            mess.setTextAlignment(Qt.AlignLeft)
            self.history_model.appendRow(mess)

        self.ui.list_messages.scrollToBottom()


    # Функция отправки собщения пользователю.
    def send_message(self):
        # Текст в поле, проверяем что поле не пустое затем забирается сообщение и поле очищается
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        try:
            msg = self.client.create_msg(message_text, self.client.account_name)
            print(msg)
            self.client.send_message(self.client.transport, msg, self.client.config['ENCODING'])
            self.client.logger.info(f'Отправлено сообщение серверу {msg["message"]}')
            pass
        except ServerError as err:
            self.messages.critical(self, 'Ошибка', err.text)
        else:
            self.history_list_update()
