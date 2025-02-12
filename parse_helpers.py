def escape_string(s):
        # Escape special characters in a string.
        s = s.replace('\\', '\\\\')
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\t', '\\t')
        return s

def dict_to_string(obj):
    """
    Convert a Python object (dict, list, tuple, str, int, float, bool, or None)
    into a string representation for encoding.
    """

    def serialize(o):
        if isinstance(o, dict):
            items = []
            for k, v in o.items():
                if not isinstance(k, str):
                    raise TypeError("Only string keys allowed in dictionaries")
                # Serialize keys (always as strings) and values.
                items.append('"' + escape_string(k) + '":' + serialize(v))
            return "{" + ",".join(items) + "}"
        elif isinstance(o, list):
            items = [serialize(item) for item in o]
            return "[" + ",".join(items) + "]"
        elif isinstance(o, tuple):
            items = [serialize(item) for item in o]
            return "(" + ",".join(items) + ")"
        elif isinstance(o, str):
            return '"' + escape_string(o) + '"'
        elif isinstance(o, bool):
            return "true" if o else "false"
        elif o is None:
            return "null"
        elif isinstance(o, (int, float)):
            return str(o)
        else:
            raise TypeError("Type not serializable: " + str(type(o)))
    return serialize(obj)


def string_to_dict(s):
    """
    Parse a string produced by dict_to_string() back into the corresponding
    Python object (dictionary, list, tuple, string, int, float, bool, or None).
    """
    i = 0  # pointer into the string

    def skip_whitespace():
        nonlocal i
        while i < len(s) and s[i] in " \t\n\r":
            i += 1

    def parse_value():
        nonlocal i
        skip_whitespace()
        if i >= len(s):
            raise ValueError("Unexpected end of input")
        if s[i] == '{':
            return parse_object()
        elif s[i] == '[':
            return parse_array()
        elif s[i] == '(':
            return parse_tuple()
        elif s[i] == '"':
            return parse_string()
        elif s[i] in '-0123456789':
            return parse_number()
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

    def parse_object():
        nonlocal i
        if s[i] != '{':
            raise ValueError("Expected '{' at position {}".format(i))
        i += 1  # skip '{'
        skip_whitespace()
        obj = {}
        if i < len(s) and s[i] == '}':
            i += 1
            return obj
        while True:
            skip_whitespace()
            if s[i] != '"':
                raise ValueError("Expected '\"' at position {} but got: {}".format(i, s[i]))
            key = parse_string()
            skip_whitespace()
            if i >= len(s) or s[i] != ':':
                raise ValueError("Expected ':' after key at position {} but got: {}".format(i, s[i] if i < len(s) else 'EOF'))
            i += 1  # skip ':'
            skip_whitespace()
            value = parse_value()
            obj[key] = value
            skip_whitespace()
            if i < len(s) and s[i] == '}':
                i += 1
                break
            elif i < len(s) and s[i] == ',':
                i += 1
            else:
                raise ValueError("Expected ',' or '}' at position {} but got: {}".format(i, s[i] if i < len(s) else 'EOF'))
        return obj

    def parse_array():
        nonlocal i
        if s[i] != '[':
            raise ValueError("Expected '[' at position {}".format(i))
        i += 1  # skip '['
        skip_whitespace()
        arr = []
        if i < len(s) and s[i] == ']':
            i += 1
            return arr
        while True:
            skip_whitespace()
            arr.append(parse_value())
            skip_whitespace()
            if i < len(s) and s[i] == ']':
                i += 1
                break
            elif i < len(s) and s[i] == ',':
                i += 1
            else:
                raise ValueError("Expected ',' or ']' at position {} but got: {}".format(i, s[i] if i < len(s) else 'EOF'))
        return arr

    def parse_tuple():
        nonlocal i
        if s[i] != '(':
            raise ValueError("Expected '(' at position {}".format(i))
        i += 1  # skip '('
        skip_whitespace()
        items = []
        if i < len(s) and s[i] == ')':
            i += 1
            return tuple(items)
        while True:
            skip_whitespace()
            items.append(parse_value())
            skip_whitespace()
            if i < len(s) and s[i] == ')':
                i += 1
                break
            elif i < len(s) and s[i] == ',':
                i += 1
            else:
                raise ValueError("Expected ',' or ')' in tuple at position {} but got: {}".format(i, s[i] if i < len(s) else 'EOF'))
        return tuple(items)

    def parse_string():
        nonlocal i
        if s[i] != '"':
            raise ValueError("Expected '\"' at position {}".format(i))
        i += 1  # skip opening quote
        result = ""
        while i < len(s):
            if s[i] == '"':
                i += 1  # skip closing quote
                return result
            elif s[i] == '\\':
                i += 1
                if i >= len(s):
                    raise ValueError("Unexpected end of string after escape")
                escape_char = s[i]
                if escape_char == '"':
                    result += '"'
                elif escape_char == '\\':
                    result += '\\'
                elif escape_char == '/':
                    result += '/'
                elif escape_char == 'n':
                    result += '\n'
                elif escape_char == 't':
                    result += '\t'
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
        if s[i] == '-':
            i += 1
        # Integer part.
        if i < len(s) and s[i] == '0':
            i += 1
        else:
            while i < len(s) and s[i].isdigit():
                i += 1
        # Fractional part.
        if i < len(s) and s[i] == '.':
            i += 1
            while i < len(s) and s[i].isdigit():
                i += 1
        # Exponent part.
        if i < len(s) and s[i] in 'eE':
            i += 1
            if i < len(s) and s[i] in '+-':
                i += 1
            while i < len(s) and s[i].isdigit():
                i += 1
        num_str = s[start:i]
        if '.' in num_str or 'e' in num_str or 'E' in num_str:
            return float(num_str)
        else:
            return int(num_str)

    # Begin parsing.
    skip_whitespace()
    result = parse_value()
    skip_whitespace()
    if i != len(s):
        raise ValueError("Extra data after valid JSON: " + s[i:])
    return result