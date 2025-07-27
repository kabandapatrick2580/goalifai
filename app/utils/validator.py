import uuid

def is_valid_string(value, min_len=1):
    return isinstance(value, str) and len(value.strip()) >= min_len

def is_valid_integer(value):
    return isinstance(value, int)

def is_valid_float(value):
    return isinstance(value, (float, int))  # ints are also valid floats

def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False

def is_valid_boolean(value):
    return isinstance(value, bool)

def is_valid_list(value):
    return isinstance(value, list)

def is_positive_number(value):
    return is_valid_float(value) and value > 0
