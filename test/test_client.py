import unittest
from client_1 import Client
from services import actions, status_code
import time
import subprocess
import sys

client = Client()


class TestClient(unittest.TestCase):

    def test_create_presence_message(self):
        account_name = 'test account'
        time_to_msg = time.ctime(time.time())
        message = {
            client.config['ACTION']: actions.PRESENCE,
            client.config['TIME']: time_to_msg,
            client.config['USER']: {
                client.config['ACCOUNT_NAME']: account_name
            }
        }
        self.assertEqual(client.create_presence_message(account_name), message, 'test_create_presence_message')

    def test_check_responce_200(self):
        response = {client.config['RESPONSE']: status_code.OK}
        self.assertEqual(client.check_responce(response), '200', 'test_check_responce')

    def test_check_responce_400(self):
        response = {
            client.config['RESPONSE']: status_code.BAD_REQUEST,
            client.config['ERROR']: 'Bad Request'
        }
        self.assertEqual(client.check_responce(response), '400', 'test_check_responce')

    def test_start_client_port(self):
        args = ['python3', 'client_1.py', '127.0.0.1', '1']
        suproc = subprocess.Popen(args, stdout=subprocess.PIPE, encoding='utf-8')
        stdout, stderr = suproc.communicate()
        self.assertEqual(stdout.replace('\n', ''), '')


if __name__ == '__main__':
    unittest.main()
