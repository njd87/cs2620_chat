import unittest
import os
import sqlite3
import json
import struct
from parse_helpers import dict_to_string, string_to_dict, escape_string
from setup import reset_database, structure_tables
from comm_server import Bolt as server_Bolt
from comm_client import Bolt as client_Bolt

class TestParseHelpers(unittest.TestCase):
    def test_escape_string(self):
        self.assertEqual(escape_string('Hello "World"'), 'Hello \"World\"')
        self.assertEqual(escape_string('Line\Break'), 'Line\\Break')
        self.assertEqual(escape_string('Tab\tTest'), 'Tab\\tTest')
        self.assertEqual(escape_string('New\nLine'), 'New\\nLine')
        self.assertEqual(escape_string('Carriage\rReturn'), 'Carriage\\rReturn')

    def test_dict_serialization(self):
        d = {"key": "value", "number": 123, "bool": True, "none": None}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_dict_serialization_empty(self):
        d = {}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_dict_serialization_nested(self):
        d = {"key": {"nested": "value"}}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_dict_serialization_list(self):
        d = {"key": ["value1", "value2"]}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)
    
    def test_dict_serialization_list_nested(self):
        d = {"key": [{"nested": "value"}]}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)
    
    def test_dict_serialization_list_empty(self):
        d = {"key": []}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)
    
    def test_dict_serialization_list_empty_nested(self):
        d = {"key": [{}]}
        s = dict_to_string(d)
        self.assertEqual(string_to_dict(s), d)

    def test_invalid_dict_serialization(self):
        d = {1: "one"}  # non-string key should raise an error
        with self.assertRaises(TypeError):
            dict_to_string(d)
    
    def test_invalid_dict_deserialization(self):
        s = 'not a valid string'
        with self.assertRaises(ValueError):
            string_to_dict(s)

class TestDatabaseSetup(unittest.TestCase):
    def test_structure_tables(self):
        structure_tables()
        with sqlite3.connect("data/messenger.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            self.assertIsNotNone(cursor.fetchone())
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages';")
            self.assertIsNotNone(cursor.fetchone())

class TestBoltCommunication(unittest.TestCase):
    def setUp(self):
        self.mock_selector = None
        self.mock_socket = None
        self.mock_addr = ('127.0.0.1', 65432)
        self.server = server_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type='json')
        self.client = client_Bolt(self.mock_selector, self.mock_socket, self.mock_addr, protocol_type='json')

    def test_protocol_type(self):
        self.client.protocol_type = 'foo'
        with self.assertRaises(ValueError):
            self.client.process_header()
    
    def test_send_receive(self):
        request = {"action": "ping", "sender": "foo", "sent_message": "Hello, World!"}
        self.client.request = request
        self.client.create_request()
        self.assertEqual(self.client.request, None)

        self.server.instream = self.client.outstream 
        self.server.process_header_len()
        self.server.process_header()
        self.server.process_request()
        self.assertEqual(self.server.request, request)
    

if __name__ == "__main__":
    unittest.main()