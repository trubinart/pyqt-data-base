import unittest
from server import Server
from services import actions, status_code
import time

server = Server()
server.load_settings()

class TestServer(unittest.TestCase):
    def test_create_presence_responce_200(self):
        account_name = 'test account'
        message = {
            server.config['ACTION']: actions.PRESENCE,
            server.config['TIME']: time.ctime(time.time()),
            server.config['USER']: {
                server.config['ACCOUNT_NAME']: account_name
            }
        }

        self.assertEqual(server.create_presence_responce(message),
                         {server.config['RESPONSE']: status_code.OK},
                         'test_create_presence_responce_200')

    def test_create_presence_responce_400(self):
        message = {
            server.config['ACTION']: actions.PRESENCE,
            server.config['TIME']: time.ctime(time.time()),
        }

        self.assertEqual(server.create_presence_responce(message),
                         {server.config['RESPONSE']: status_code.BAD_REQUEST,
                             server.config['ERROR']: 'Bad Request'},
                         'test_create_presence_responce_400')

if __name__ == '__main__':
    unittest.main()
