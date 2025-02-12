import unittest
from parse_helpers import *

class TestSerializationFunctions(unittest.TestCase):
    def test_empty_dict(self):
        d = {}
        s = dict_to_string(d)
        self.assertEqual(s, "{}")
        self.assertEqual(string_to_dict(s), d)

    def test_empty_list(self):
        lst = []
        s = dict_to_string(lst)
        self.assertEqual(s, "[]")
        self.assertEqual(string_to_dict(s), lst)

    def test_empty_tuple(self):
        t = ()
        s = dict_to_string(t)
        self.assertEqual(s, "()")
        self.assertEqual(string_to_dict(s), t)

    def test_simple_dict(self):
        d = {"key": "value", "number": 123, "bool": True, "none": None}
        s = dict_to_string(d)
        d2 = string_to_dict(s)
        self.assertEqual(d2, d)

    def test_nested_dict_and_list(self):
        d = {
            "list": [1, 2, {"nested": "value"}],
            "dict": {"inner_list": [True, False, None]}
        }
        s = dict_to_string(d)
        d2 = string_to_dict(s)
        self.assertEqual(d2, d)

    def test_nested_tuples(self):
        t = ((1, 2), (3, (4, 5)))
        s = dict_to_string(t)
        self.assertEqual(string_to_dict(s), t)

    def test_single_element_tuple(self):
        t = (42,)
        s = dict_to_string(t)
        # Note: The serializer produces "(42)" for a single element tuple.
        self.assertEqual(s, "(42)")
        self.assertEqual(string_to_dict(s), t)

    def test_multi_element_tuple(self):
        t = (1, 2, 3)
        s = dict_to_string(t)
        self.assertEqual(s, "(1,2,3)")
        self.assertEqual(string_to_dict(s), t)

    def test_tuple_with_list_and_dict(self):
        t = ({"a": [1, 2, 3]}, [4, 5, {"b": (6, 7)}])
        s = dict_to_string(t)
        self.assertEqual(string_to_dict(s), t)

    def test_string_escape(self):
        s_orig = "Line1\nLine2\tTabbed"
        d = {"text": s_orig}
        s = dict_to_string(d)
        d2 = string_to_dict(s)
        self.assertEqual(d2, d)

    def test_number_formats(self):
        d = {"int": 42, "float": 3.1415, "negative": -100, "exp": 1e-5}
        s = dict_to_string(d)
        d2 = string_to_dict(s)
        self.assertEqual(d2, d)

    def test_boolean_values(self):
        d = {"true_val": True, "false_val": False}
        s = dict_to_string(d)
        d2 = string_to_dict(s)
        self.assertEqual(d2, d)

    def test_non_string_key_error(self):
        d = {1: "one"}  # non-string key should raise an error
        with self.assertRaises(TypeError):
            dict_to_string(d)

    def test_extra_data_in_string(self):
        # If extra data exists after a valid JSON object, a ValueError should be raised.
        valid_serialized = dict_to_string({"key": "value"})
        bad_serialized = valid_serialized + " extra"
        with self.assertRaises(ValueError):
            string_to_dict(bad_serialized)

    def test_invalid_json_input(self):
        # Provide a malformed string that should trigger a ValueError.
        malformed = '{"key": "value", "missing_end": [1, 2, 3'
        with self.assertRaises(ValueError):
            string_to_dict(malformed)

# ---------------- Run the tests -----------------

if __name__ == '__main__':
    unittest.main()