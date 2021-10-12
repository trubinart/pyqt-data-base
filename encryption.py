import os
from binascii import hexlify
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
import hashlib
import binascii

def padding_text(text):
    ''' Выравнивание сообщения до длины, кратной 16 байтам.
        В данном случае исходное сообщение дополняется пробелами.
    '''
    pad_len = (16 - len(text) % 16) % 16
    return text + b' ' * pad_len

def _encrypt(plaintext, key):
    ''' Шифрование сообщения plaintext ключом key.
        Атрибут iv - вектор инициализации для алгоритма шифрования.
        Если не задается явно при создании объекта-шифра, генерируется случайно.
        Его следует добавить в качестве префикса к финальному шифру,
        чтобы была возможность правильно расшифровать сообщение.
    '''
    keys = hashlib.sha256(key).digest()
    plaintext_1 = plaintext.encode('utf-8')
    plaintext_2 = padding_text(plaintext_1)
    cipher = AES.new(keys, AES.MODE_CBC)
    ciphertext = cipher.iv + cipher.encrypt(plaintext_2)
    return ciphertext

def _decrypt(ciphertext, key):
    ''' Расшифровка шифра ciphertext ключом key.
        Вектор инициализации берется из исходного шифра.
        Его длина для большинства режимов шифрования всегда 16 байт.
        Расшифровываться будет оставшаяся часть шифра.
    '''
    keys = hashlib.sha256(key).digest()
    cipher = AES.new(keys, AES.MODE_CBC, iv=ciphertext[:16])
    msg = cipher.decrypt(ciphertext[16:])
    result = msg.decode('utf-8').strip()
    return result


if __name__ == '__main__':
    account_name = 'test'
    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{account_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())
            keys_2 = keys.exportKey()


    text = 'Hi'
    enc = _encrypt(text, keys_2)
    text_to =  binascii.hexlify(enc)

    print(enc)
    print(type(text_to))

    y = str(text_to, 'ascii')

    print(y)
    print(type(y))

    x = binascii.unhexlify(y)

    print(x)
    print(type(x))

    dec = _decrypt(x, keys_2)
    print(dec)