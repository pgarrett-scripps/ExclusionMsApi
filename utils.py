def convert_int(val):
    if val == 'None' or val == '':
        return None
    return int(val)


def convert_float(val):
    if val == 'None' or val == '':
        return None
    return float(val)


def convert_str(val):
    if val == 'None' or val == '':
        return None
    return str(val)
