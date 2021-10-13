
class ServerError(Exception):
    '''Исключение - ошибка сервера'''
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text



class ReqFieldMissingError(Exception):
    '''Ошибка - отсутствует обязательное поле в принятом словаре.'''
    def __init__(self, missing_field):
        self.missing_field = missing_field

    def __str__(self):
        return f'В принятом словаре отсутствует обязательное поле {self.missing_field}.'
