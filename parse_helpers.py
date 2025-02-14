def escape_string(s):
    # Escape special characters in a string.
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    return s


def dict_to_string(obj):
    """
    Convert a Python object (dict, list, tuple, str, int, float, bool, or None)
    into a string representation for encoding.

    Parameters:
    ----------
    obj : dict
        The object to serialize.
    """
    if isinstance(obj, dict):
        items = []
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError("Only string keys allowed in dictionaries")
            # Serialize keys (always as strings) and values.
            items.append('"' + escape_string(k) + '":' + dict_to_string(v))
        return "{" + ",".join(items) + "}"
    # sometimes things will be nested, so for nested items, we need to chek for list/typle
    elif isinstance(obj, list):
        items = [dict_to_string(item) for item in obj]
        return "[" + ",".join(items) + "]"
    elif isinstance(obj, tuple):
        items = [dict_to_string(item) for item in obj]
        return "(" + ",".join(items) + ")"

    # then check for primitive types
    elif isinstance(obj, str):
        return '"' + escape_string(obj) + '"'
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif obj is None:
        return "null"
    elif isinstance(obj, (int, float)):
        return str(obj)
    # anything else is not serializable
    else:
        raise TypeError("Type not serializable: " + str(type(obj)))


def string_to_dict(s):
    """
    Parse a string produced by dict_to_string() back into the corresponding
    Python object (dictionary, list, tuple, string, int, float, bool, or None).
    """
    # position in the string
    i = 0

    # skip over whitespace
    # nonlocal is used to modify the variable in the parent scope
    def skip_whitespace():
        nonlocal i
        while i < len(s) and s[i] in " \t\n\r":
            i += 1

    # keep moving the pointer until we reach some hardcoded characters
    def parse_value():
        nonlocal i
        skip_whitespace()
        if i >= len(s):
            raise ValueError("Unexpected end of input")

        # we got to another dictionary
        if s[i] == "{":
            return parse_dict()
        # we got to a list
        elif s[i] == "[":
            return parse_array()
        # we got to a tuple
        elif s[i] == "(":
            return parse_tuple()
        # we got to a string
        elif s[i] == '"':
            return parse_string()
        elif s[i] in "-0123456789":
            return parse_number()

        # check for the primitive types
        elif s.startswith("true", i):
            i += 4
            return True
        elif s.startswith("false", i):
            i += 5
            return False
        elif s.startswith("null", i):
            i += 4
            return None
        else:
            raise ValueError("Unexpected character at position {}: {}".format(i, s[i]))

    def parse_dict():
        nonlocal i
        if s[i] != "{":
            raise ValueError("Expected '{' at position {}".format(i))
        i += 1  # skip '{'
        skip_whitespace()
        obj = {}
        if i < len(s) and s[i] == "}":
            i += 1
            return obj
        while True:
            skip_whitespace()
            if s[i] != '"':
                # need key to be string
                raise ValueError(
                    "Expected '\"' at position {} but got: {}".format(i, s[i])
                )
            key = parse_string()
            skip_whitespace()
            if i >= len(s) or s[i] != ":":
                # should expect a colon after the key
                raise ValueError(
                    "Expected ':' after key at position {} but got: {}".format(
                        i, s[i] if i < len(s) else "EOF"
                    )
                )
            i += 1  # skip ':'
            skip_whitespace()
            value = parse_value()
            obj[key] = value
            skip_whitespace()
            # check if we reached the end of the dictionary
            if i < len(s) and s[i] == "}":
                i += 1
                break
            elif i < len(s) and s[i] == ",":
                i += 1
            else:
                raise ValueError(
                    "Expected ',' or '}' at position {} but got: {}".format(
                        i, s[i] if i < len(s) else "EOF"
                    )
                )
        return obj

    def parse_array():
        nonlocal i
        if s[i] != "[":
            raise ValueError("Expected '[' at position {}".format(i))
        i += 1  # skip '['
        skip_whitespace()
        arr = []
        if i < len(s) and s[i] == "]":
            i += 1
            return arr
        while True:
            skip_whitespace()
            arr.append(parse_value())
            skip_whitespace()
            # check if we reached the end of the array
            if i < len(s) and s[i] == "]":
                i += 1
                break
            elif i < len(s) and s[i] == ",":
                i += 1
            else:
                raise ValueError(
                    "Expected ',' or ']' at position {} but got: {}".format(
                        i, s[i] if i < len(s) else "EOF"
                    )
                )
        return arr

    # a lot of the logic for tuple is the same as array
    # in fact, when we parse a tuple, we want to change it to a list
    def parse_tuple():
        nonlocal i
        if s[i] != "(":
            raise ValueError("Expected '(' at position {}".format(i))
        i += 1
        skip_whitespace()
        items = []
        if i < len(s) and s[i] == ")":
            i += 1
            return items
        while True:
            skip_whitespace()
            items.append(parse_value())
            skip_whitespace()
            if i < len(s) and s[i] == ")":
                i += 1
                break
            elif i < len(s) and s[i] == ",":
                i += 1
            else:
                raise ValueError(
                    "Expected ',' or ')' in tuple at position {} but got: {}".format(
                        i, s[i] if i < len(s) else "EOF"
                    )
                )
        return items

    def parse_string():
        nonlocal i
        if s[i] != '"':
            raise ValueError("Expected '\"' at position {}".format(i))
        i += 1
        result = ""
        while i < len(s):
            if s[i] == '"':
                i += 1
                return result
            elif s[i] == "\\":
                i += 1
                if i >= len(s):
                    raise ValueError("Unexpected end of string after escape")
                escape_char = s[i]
                if escape_char == '"':
                    result += '"'
                elif escape_char == "\\":
                    result += "\\"
                elif escape_char == "/":
                    result += "/"
                elif escape_char == "n":
                    result += "\n"
                elif escape_char == "t":
                    result += "\t"
                else:
                    result += escape_char
                i += 1
            else:
                result += s[i]
                i += 1
        raise ValueError("Unterminated string literal")

    def parse_number():
        nonlocal i
        start = i
        if s[i] == "-":
            i += 1

        # numeric part
        if i < len(s) and s[i] == "0":
            i += 1
        else:
            while i < len(s) and s[i].isdigit():
                i += 1
        # check for floats
        if i < len(s) and s[i] == ".":
            i += 1
            while i < len(s) and s[i].isdigit():
                i += 1
        # if number is too large or too small, it will be in scientific notation
        if i < len(s) and s[i] in "eE":
            i += 1
            if i < len(s) and s[i] in "+-":
                i += 1
            while i < len(s) and s[i].isdigit():
                i += 1
        num_str = s[start:i]
        if "." in num_str or "e" in num_str or "E" in num_str:
            return float(num_str)
        else:
            return int(num_str)

    # actual parsin
    skip_whitespace()
    result = parse_value()
    skip_whitespace()
    if i != len(s):
        raise ValueError("Extra data: " + s[i:])
    return result
