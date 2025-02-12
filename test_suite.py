import unittest
import os
import sqlite3
import json
import struct
from parse_helpers import dict_to_string, string_to_dict, escape_string
from setup import reset_database, structure_tables
from comm_server import Bolt as server_Bolt
from comm_client import Bolt as client_Bolt

unittest.TestLoader.sortTestMethodsUsing = None

class TestParseHelpers(unittest.TestCase):
    '''
    Test cases for the parse_helpers module.

    Tests the following functions:
    - dict_to_string
    - string_to_dict
    '''

    def test_dict_serialization(self):
        # check regular dictionary serialziation
        d = {"key": "value", "number": 123, "bool": True, "none": None}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_dict_serialization_empty(self):
        # check edge case, empty dict
        d = {}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_dict_serialization_nested(self):
        # check nested dictionary serialization
        d = {"key": {"nested": "value"}}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_dict_serialization_list(self):
        # check list serialization
        d = {"key": ["value1", "value2"]}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)
    
    def test_dict_serialization_list_nested(self):
        # check nested list serialization
        d = {"key": [{"nested": "value"}]}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)
    
    def test_dict_serialization_list_empty(self):
        # check empty list serialization
        d = {"key": []}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)
    
    def test_dict_serialization_list_empty_nested(self):
        # check empty nested list serialization
        d = {"key": [{}]}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_invalid_dict_serialization(self):
        # check invalid dictionary serialization, since keys must be strings
        d = {1: "one"}
        with self.assertRaises(TypeError):
            dict_to_string(d)
    
    def test_invalid_dict_deserialization(self):
        # check invalid dictionary deserialization, since keys must be strings
        s = 'not a valid string'
        with self.assertRaises(ValueError):
            string_to_dict(s)

class TestDatabaseSetup(unittest.TestCase):
    '''
    Tests "setup.py" file for resetting and structuring the database.

    Tests the following functions:
    - reset_database
    - structure_tables
    '''
    def test_reset_database(self):
        # check if the database file is deleted
        reset_database()
        self.assertFalse(os.path.exists("data/messenger.db"))

    def test_structure_tables(self):
        # check if the tables are created correctly
        structure_tables()
        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        self.assertIsNotNone(cursor.fetchone())
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages';")
        self.assertIsNotNone(cursor.fetchone())
        conn.commit()
        conn.close()

class TestProtocolMethodsJson(unittest.TestCase):
    '''
    Test cases for the protocol methods in the Bolt class via encoding and decoding.

    Tests the following functions:
    - _byte_encode
    - _byte_decode
    '''
    def setUp(self):
        self.client_Bolt = client_Bolt(None, None, None, protocol_type='json', gui=None)
        self.server_Bolt = server_Bolt(None, None, None, protocol_type='json')

    def test_encode_json(self):
        data = {"key": "value"}
        # encode the data to bytes
        encoded_data = self.client_Bolt._byte_encode(data, 'utf-8')

        # decode the bytes back to the original data
        decoded_data = self.client_Bolt._byte_decode(encoded_data, 'utf-8')
        self.assertEqual(decoded_data, data)

        # do the same for server
        encoded_data = self.server_Bolt._byte_encode(data, 'utf-8')
        decoded_data = self.server_Bolt._byte_decode(encoded_data, 'utf-8')

        self.assertEqual(decoded_data, data)

    def test_nested_json(self):
        data = {"key": {"nested": "value"}}
        # encode the data to bytes
        encoded_data = self.client_Bolt._byte_encode(data, 'utf-8')

        # decode the bytes back to the original data
        decoded_data = self.client_Bolt._byte_decode(encoded_data, 'utf-8')
        self.assertEqual(decoded_data, data)

        # do the same for server
        encoded_data = self.server_Bolt._byte_encode(data, 'utf-8')
        decoded_data = self.server_Bolt._byte_decode(encoded_data, 'utf-8')

        self.assertEqual(decoded_data, data)

    def test_edge_case_json(self):
        data = {"key": {"nested": "value"}, 'key2': '-1', 'key3': None}
        # encode the data to bytes
        encoded_data = self.client_Bolt._byte_encode(data, 'utf-8')

        # decode the bytes back to the original data
        decoded_data = self.client_Bolt._byte_decode(encoded_data, 'utf-8')
        self.assertEqual(decoded_data, data)

        # do the same for server
        encoded_data = self.server_Bolt._byte_encode(data, 'utf-8')
        decoded_data = self.server_Bolt._byte_decode(encoded_data, 'utf-8')

        self.assertEqual(decoded_data, data)


class TestProtocolMethodsCustom(unittest.TestCase):
    def setUp(self):
        self.client_Bolt = client_Bolt(None, None, None, protocol_type='custom', gui=None)
        self.server_Bolt = server_Bolt(None, None, None, protocol_type='custom')

    def test_encode_custom(self):
        data = {"key": "value"}
        # encode the data to bytes
        encoded_data = self.client_Bolt._byte_encode(data, 'utf-8')

        # decode the bytes back to the original data
        decoded_data = self.client_Bolt._byte_decode(encoded_data, 'utf-8')
        self.assertEqual(decoded_data, data)

        # do the same for server
        encoded_data = self.server_Bolt._byte_encode(data, 'utf-8')
        decoded_data = self.server_Bolt._byte_decode(encoded_data, 'utf-8')

        self.assertEqual(decoded_data, data)

    def test_nested_custom(self):
        data = {"key": {"nested": "value"}}
        # encode the data to bytes
        encoded_data = self.client_Bolt._byte_encode(data, 'utf-8')

        # decode the bytes back to the original data
        decoded_data = self.client_Bolt._byte_decode(encoded_data, 'utf-8')
        self.assertEqual(decoded_data, data)

        # do the same for server
        encoded_data = self.server_Bolt._byte_encode(data, 'utf-8')
        decoded_data = self.server_Bolt._byte_decode(encoded_data, 'utf-8')

        self.assertEqual(decoded_data, data)

    def test_edge_case_custom(self):
        data = {"key": {"nested": "value"}, 'key2': '-1', 'key3': None}
        # encode the data to bytes
        encoded_data = self.client_Bolt._byte_encode(data, 'utf-8')

        # decode the bytes back to the original data
        decoded_data = self.client_Bolt._byte_decode(encoded_data, 'utf-8')
        self.assertEqual(decoded_data, data)

        # do the same for server
        encoded_data = self.server_Bolt._byte_encode(data, 'utf-8')
        decoded_data = self.server_Bolt._byte_decode(encoded_data, 'utf-8')

        self.assertEqual(decoded_data, data)

class TestSendReceiveJSON(unittest.TestCase):
    '''
    Test cases for the send and receive methods in the Bolt class via JSON encoding and decoding.
    '''
    def setUp(self):
        self.mock_selector = None
        self.mock_socket = None
        self.mock_addr = ('127.0.0.1', 65432)
        self.mock_gui = None  # Dummy GUI input
        self.server = server_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type='json')
        self.client = client_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type='json', gui=self.mock_gui)

    def test_protocol_type(self):
        self.client.protocol_type = 'foo'
        with self.assertRaises(ValueError):
            self.client.process_header()
    
    def test_send_receive(self):
        request = {"action": "ping", "sender": "foo", "sent_message": "Hello, World!", "encoding": "utf-8"}
        self.client.request = request
        self.client.create_request()
        self.assertEqual(self.client.request, None)

        self.server.instream = self.client.outstream 
        self.server.process_header_len()
        self.server.process_header()
        try:
            self.server.process_request()
        except AttributeError:
            pass
        del request["encoding"]
        self.assertEqual(self.server.request, request)

class TestSendReceiveJSON(unittest.TestCase):
    '''
    Test cases for the send and receive methods in the Bolt class via JSON encoding and decoding.
    '''
    def setUp(self):
        self.mock_selector = None
        self.mock_socket = None
        self.mock_addr = ('127.0.0.1', 65432)
        self.mock_gui = None  # Dummy GUI input
        self.server = server_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type='custom')
        self.client = client_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type='custom', gui=self.mock_gui)

    def test_protocol_type(self):
        self.client.protocol_type = 'foo'
        with self.assertRaises(ValueError):
            self.client.process_header()
    
    def test_send_receive(self):
        request = {"action": "ping", "sender": "foo", "sent_message": "Hello, World!", "encoding": "utf-8"}
        self.client.request = request
        self.client.create_request()
        self.assertEqual(self.client.request, None)

        self.server.instream = self.client.outstream 
        self.server.process_header_len()
        self.server.process_header()
        try:
            self.server.process_request()
        except AttributeError:
            pass
        del request["encoding"]
        self.assertEqual(self.server.request, request)

class TestServerProcessResponse(unittest.TestCase):
    '''
    Test cases for communicating between the server and client via JSON encoding and decoding.
    '''
    protocol_type = 'json'
    
    @classmethod
    def setUpClass(cls):
        # Code to run once at the beginning of the test class
        reset_database()
        structure_tables()
    def setUp(self):
        self.mock_selector = None
        self.mock_socket = None
        self.mock_addr = ('127.0.0.1', 65432)
        self.mock_gui = None  # Dummy GUI input
        self.server = server_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type=self.protocol_type)
        self.client = client_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type=self.protocol_type, gui=self.mock_gui)

    def test1a_check_username_none(self):
        # check if username is None, it should return False
        request = {"action": "check_username", "username": "foo"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], False)

    def test1b_register_user(self):
        # register user, check if it exists in the database
        request = {"action": "register", "username": "foo", "passhash": "bar"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], True)
        self.assertEqual(self.client.response["users"], [])

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username='foo';")
        user = cursor.fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user[1], 'foo')
        cursor.execute("SELECT COUNT(*) FROM users;")
        count = cursor.fetchone()[0]

        # should be in database now
        self.assertEqual(count, 1)
        conn.close()

    def test1c_register_user_exists(self):
        # if user already exists, it should return False
        request = {"action": "register", "username": "foo", "passhash": "bar"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], False)

        # double check if user is in database
        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username='foo';")
        user = cursor.fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user[1], 'foo')
        cursor.execute("SELECT COUNT(*) FROM users;")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        conn.close()

    def test1d_login_user(self):
        # login existing user, check return true
        request = {"action": "login", "username": "foo", "passhash": "bar"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], True)

    def test1e_login_user_invalid(self):
        # login with invalid password, should return False
        request = {"action": "login", "username": "foo", "passhash": "baz"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], False)

    def test1f_register_other(self):
        # register another user, check if it exists in the database
        request = {"action": "register", "username": "bar", "passhash": "baz"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], True)
        self.assertEqual(self.client.response["users"], ["foo"])
    
    def test2a_send_message(self):
        # send message between two users, check if it exists in the database
        request = {"action": "send_message", "sender": "foo", "recipient": "bar", "message": "Hello, World!"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertIsNotNone(self.client.response["message_id"])

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE message_id=?;", (self.client.response["message_id"],))
        message = cursor.fetchone()
        self.assertIsNotNone(message)
        self.assertEqual(message[1], 'foo')
        self.assertEqual(message[2], 'bar')
        self.assertEqual(message[3], 'Hello, World!')
        conn.close()

    def test2b_send_many_msgs(self):
        # send many messages between two users, check if they exist in the database
        for i in range(1000):
            request = {"action": "send_message", "sender": "foo", "recipient": "bar", "message": f"Message {i}"}
            self.server.request = request

            self.server.create_response()
            self.client.instream = self.server.outstream
            self.client.process_header_len()
            self.client.process_header()
            try:
                self.client.process_response()
            except AttributeError:
                pass
            self.assertIsNotNone(self.client.response["message_id"])

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE sender='foo' AND recipient='bar';")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1001)
        conn.close()

    def test3a_ping(self):
        # ping user, check if message is delivered
        request = {"action": "ping", "sender": "foo", "sent_message": "Hello, World!", "message_id": 1}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE sender='foo' AND delivered=1;")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        conn.close()

    def test3b_load_chat(self):
        # load chat between two users, check if messages are returned
        request = {"action": "load_chat", "username": "foo", "user2": "bar"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertIn(self.client.response["messages"][0], [['foo', 'bar', 'Hello, World!', 1], ('foo', 'bar', 'Hello, World!', 1)])

    def test3c_load_chat_empty(self):
        # check to make sure empty chat returns no messages
        request = {"action": "load_chat", "username": "foo", "user2": "baz"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["messages"], [])

    def test4a_view_undelivered(self):
        # view undelivered messages, check if they are returned
        request = {"action": "view_undelivered", "username": "bar", "n_messages": 10}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass

        # check if undelieverd are marked as delivered
        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE recipient='bar' AND delivered=0;")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()

    def test5a_delete_message(self):
        # delete message, check if it is removed from the database
        request = {"action": "delete_message", "message_id": 1}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE message_id=1;")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()

    def test5b_delete_account_invalid_pass(self):
        # delete account with invalid password, should return False
        request = {"action": "delete_account", "username": "foo", "passhash": "baz"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], False)

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='foo';")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

        cursor.execute("SELECT COUNT(*) FROM messages WHERE sender='foo' OR recipient='foo';")
        count = cursor.fetchone()[0]
        self.assertNotEqual(count, 0)
        conn.close()

    def test5c_delete_account_invalid_user(self):
        # delete account with invalid username, should return False
        request = {"action": "delete_account", "username": "baz", "passhash": "bar"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], False)

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='baz';")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()

    def test5d_delete_account(self):
        # delete account, check if it is removed from the database
        request = {"action": "delete_account", "username": "foo", "passhash": "bar"}
        self.server.request = request

        self.server.create_response()
        self.client.instream = self.server.outstream
        self.client.process_header_len()
        self.client.process_header()
        try:
            self.client.process_response()
        except AttributeError:
            pass
        self.assertEqual(self.client.response["result"], True)

        conn = sqlite3.connect("data/messenger.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='foo';")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)

        cursor.execute("SELECT COUNT(*) FROM messages WHERE sender='foo' OR recipient='foo';")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()

class TestServerProcessResponseCustom(TestServerProcessResponse):
    protocol_type = 'custom'
        

if __name__ == "__main__":
    unittest.main()

'''
Manual UI unit tests:

- Correctly register a user
- Correctly login a user
- Correctly fails login with incorrect password
- Correctly fails register with existing user
- Correctly fails to submit empty message/usernames
- Correctly reads undelivered messages
- Correctly selects number of undelivered messages
- Correctly sends messages live
- Correctly sends pings
- Correctly deletes own messages
- Correctly fails to delete other users' messages
- Correctly deletes own account
- Correctly fails to delete other users' accounts
- Correctly pings users' "users" tab when user deletes
- Correctly pings users' "users" tab when user registers
- Correctly loads chat history for existing chat
- Correctly loads chat history for non-existing chat
- Correctly fails to delete account with incorrect password

'''