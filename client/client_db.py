import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker


# Класс - отображение таблицы истории сообщений
class MessageHistory:
    def __init__(self, from_user, to_user, message):
        self.id = None
        self.from_user = from_user
        self.to_user = to_user
        self.message = message
        self.date = datetime.datetime.now()


class ClientDatabase():
    # Конструктор класса:
    def __init__(self, name):
        self.database_engine = create_engine(f'sqlite:///client_{name}.db3?check_same_thread=False', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу истории сообщений
        history = Table('message_history', self.metadata,
                        Column('id', Integer, primary_key=True),
                        Column('from_user', String),
                        Column('to_user', String),
                        Column('message', Text),
                        Column('date', DateTime)
                        )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        mapper(MessageHistory, history)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        self.session.commit()

    # Функция сохраняющяя сообщения
    def save_message(self, from_user, to_user, message):
        message_row = MessageHistory(from_user, to_user, message)
        self.session.add(message_row)
        self.session.commit()

    # Функция возвращающая историю переписки
    def get_history(self, from_who=None, to_who=None):
        query = self.session.query(MessageHistory)
        if from_who:
            query = query.filter_by(from_user=from_who)
        if to_who:
            query = query.filter_by(to_user=to_who)
        return [(history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                for history_row in query.all()]

if __name__ == '__main__':
    test_db = ClientDatabase('test1')