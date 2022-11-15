import dataclasses


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


@dataclasses.dataclass
class Offset:
    mass: float = 0
    rt: float = 0
    ook0: float = 0
    intensity: float = 0

    def clear(self):
        self.mass = 0
        self.rt = 0
        self.ook0 = 0
        self.intensity = 0