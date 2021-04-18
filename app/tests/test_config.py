import unittest

from app.api.config import *


class TestConfig(unittest.TestCase):

    def test_default_config_exists(self):
        # when/then
        self.assertEqual(DEFAULT_SERVER_ADDRESS, config.server_address)
        self.assertIsNone(config.basic_auth_username)
        self.assertIsNone(config.basic_auth_password)
        self.assertEqual(DEFAULT_WEBHOOK_URL, config.webhook_url)
        self.assertEqual(DEFAULT_ACCESSORY_ID, config.accessory_id)
        self.assertFalse(config.is_basic_auth_active())

    def test_config_reads_from_environment(self):
        # setup
        os.environ[SERVER_ADDRESS] = 'http://testaddress'
        os.environ[BASIC_AUTH_USERNAME] = 'user'
        os.environ[BASIC_AUTH_PASSWORD] = 'password'
        os.environ[WEBHOOK_URL] = 'http://testhook'
        os.environ[ACCESSORY_ID] = 'testaccessory'
        # when
        test_config = Config()
        # then
        self.assertEqual('http://testaddress', test_config.server_address)
        self.assertEqual('user', test_config.basic_auth_username)
        self.assertEqual('password', test_config.basic_auth_password)
        self.assertEqual('http://testhook', test_config.webhook_url)
        self.assertEqual('testaccessory', test_config.accessory_id)
        self.assertTrue(test_config.is_basic_auth_active())
        # cleanup
        os.unsetenv(SERVER_ADDRESS)
        os.unsetenv(BASIC_AUTH_USERNAME)
        os.unsetenv(BASIC_AUTH_PASSWORD)
        os.unsetenv(WEBHOOK_URL)
        os.unsetenv(ACCESSORY_ID)
