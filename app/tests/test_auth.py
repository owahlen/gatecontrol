import unittest

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from app.api import auth
from app.api.config import config


class TestAuth(unittest.TestCase):

    def test_successful_authorize_request(self):
        # setup
        credentials = HTTPBasicCredentials(username="foo", password="bar")
        config.basic_auth_username = "foo"
        config.basic_auth_password = "bar"
        # when
        auth.authorize_request(credentials)
        # then assert no exception was thrown
        # cleanup
        config.basic_auth_username = None
        config.basic_auth_password = None

    def test_unsuccessful_authorize_request(self):
        # setup
        credentials = HTTPBasicCredentials(username="foo", password="bar")
        config.basic_auth_username = "foo"
        config.basic_auth_password = "incorrect"
        # when/then
        self.assertRaises(HTTPException, auth.authorize_request, credentials)
        # cleanup
        config.basic_auth_username = None
        config.basic_auth_password = None
