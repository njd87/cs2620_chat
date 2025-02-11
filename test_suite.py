import unittest
from parse_helpers import *

class TestParseHelpers(unittest.TestCase):
    def test_dict_to_list(self):
        self.assertEqual(dict_to_list({"action": "login"}, True), ["login", None, None, None, None, None, None, None, None, None])
        self.assertEqual(dict_to_list({"result": "success"}, False), ["success", None, None, None, None, None, None])
        self.assertEqual(dict_to_list({"action": "send_message", "sender": "test", "recipient": "test", "message": "test"}, True), ["send_message", None, None, None, "test", "test", "test", None, None, None])
        self.assertEqual(dict_to_list({"message_id": 1}, False), [None, None, None, None, 1, None, None])

    def test_list_to_dict(self):
        self.assertEqual(list_to_string(["login", "test", "test", None, None, None, None, None, None, None]), "login,test,test,None,None,None,None,None,None,None")
        self.assertEqual(list_to_string(["success", None, None, None, None, None, None]), "success,None,None,None,None,None,None")



# runs all the tests
unittest.main()

