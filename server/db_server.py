import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker

class AllUsers:
    def __init__(self, username,passwd_hash):
        self.name = username
        self.last_login = datetime.datetime.now()
        self.passwd_hash = passwd_hash
        self.pubkey = None
        self.id = None


class ActiveUsers:
    def __init__(self, user_id, ip_address, port, login_time):
        self.user = user_id
        self.ip_address = ip_address
        self.port = port
        self.login_time = login_time
        self.id = None


class LoginHistory:
    def __init__(self, name, date, ip, port):
        self.id = None
        self.name = name
        self.date_time = date
        self.ip = ip
        self.port = port

# Класс отображение таблицы истории действий
class MessageHistory:
    def __init__(self, user, message):
        self.user = user
        self.message = message
        self.data = datetime.datetime.now()
        self.id = None

class ServerStorage:
    def __init__(self):
        self.database_engine = create_engine('sqlite:///bd_server.db3?check_same_thread=False', echo=False, pool_recycle=7200)

        self.metadata = MetaData()

        # Создаём таблицу пользователей
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime),
                            Column('passwd_hash', String),
                            Column('pubkey', Text)
                            )

        # Создаём таблицу активных пользователей
        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Создаём таблицу истории входов
        user_login_history = Table('Login_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('Users.id')),
                                   Column('date_time', DateTime),
                                   Column('ip', String),
                                   Column('port', String)
                                   )

        # Создаём таблицу истории пользователей
        massage_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('message', Text),
                                    Column('data', DateTime))

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        # Связываем класс в ORM с таблицей
        mapper(AllUsers, users_table)
        mapper(ActiveUsers, active_users_table)
        mapper(LoginHistory, user_login_history)
        mapper(MessageHistory, massage_history_table)


        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей
        self.session.query(ActiveUsers).delete()
        self.session.commit()

    # Функция выполняющаяся при входе пользователя, записывает в базу факт входа
    def user_login(self, username, ip_address, port, pub_key):
        rez = self.session.query(AllUsers).filter_by(name=username)
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
            user.pubkey = pub_key
        else:
            user = AllUsers(username)
            self.session.add(user)
            self.session.commit()

        new_active_user = ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        history = LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        self.session.commit()

    # Функция фиксирующая отключение пользователя
    def user_logout(self, username):
        user = self.session.query(AllUsers).filter_by(name=username).first()
        self.session.query(ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    # Функция возвращающая историю входов по пользователю или всем пользователям
    def login_history(self, username=None):
        query = self.session.query(AllUsers.name,
                                   LoginHistory.date_time,
                                   LoginHistory.ip,
                                   LoginHistory.port
                                   ).join(AllUsers)
        if username:
            query = query.filter(AllUsers.name == username)
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(
            AllUsers.name,
            ActiveUsers.ip_address,
            ActiveUsers.port,
            ActiveUsers.login_time
        ).join(AllUsers)
        # Возвращаем список кортежей
        return query.all()

    def write_message_history(self, username, message):
        user = self.session.query(AllUsers).filter_by(name=username).first()
        new_history_line = MessageHistory(user.id, message)
        self.session.add(new_history_line)
        self.session.commit()

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            AllUsers.name,
            AllUsers.last_login,
            MessageHistory.message,
            MessageHistory.data
        ).join(AllUsers)
        # Возвращаем список кортежей
        return query.all()

    def check_user(self, name):
        '''Метод проверяющий существование пользователя.'''
        if self.session.query(AllUsers).filter_by(name=name).count():
            return True
        else:
            return False

    def add_user(self, name, passwd_hash):
        '''
        Метод регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики.
        '''
        user_row = AllUsers(name, passwd_hash)
        self.session.add(user_row)
        self.session.commit()

    def get_hash(self, name):
        '''Метод получения хэша пароля пользователя.'''
        user = self.session.query(AllUsers).filter_by(name=name).first()
        return user.passwd_hash

    def get_keys(self, name):
        '''Метод получения хэша пароля пользователя.'''
        user = self.session.query(AllUsers).filter_by(name=name).first()
        return user.pubkey

if __name__ == '__main__':
    test_db = ServerStorage()
    test_db.user_login('client_1', '192.168.1.4', 7666)
    test_db.write_message_history('client_1', 'mes')
    # test_db.user_logout('client_1')
    print(test_db.message_history())

