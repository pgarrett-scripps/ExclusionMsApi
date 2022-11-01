import logging
import random
import sys
from dataclasses import dataclass, asdict
from typing import Union

from .exceptions import IncorrectToleranceException

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


@dataclass(eq=True)
class ExclusionInterval():
    """
    Represents an interval in the excluded space.

    id: The Id of the interval. Does not have to be unique. If None: Represents all IDs.
    charge: The charge of the excluded interval. If None: the Interval represents all charges
    min_bounds: The lower 'inclusive' bound of the interval. If None: Will be set to sys.float_info.min
    max_bounds: The upper 'exclusive' bound of the interval. If None: Will be set to sys.float_info.max
    """
    id: Union[str, None]
    charge: Union[int, None]
    min_mass: Union[float, None]
    max_mass: Union[float, None]
    min_rt: Union[float, None]
    max_rt: Union[float, None]
    min_ook0: Union[float, None]
    max_ook0: Union[float, None]
    min_intensity: Union[float, None]
    max_intensity: Union[float, None]

    def convert_none(self):
        """
        If any bounds are None, set them to either min/max float
        """

        if self.min_mass is None:
            self.min_mass = sys.float_info.min

        if self.max_mass is None:
            self.max_mass = sys.float_info.max

        if self.min_rt is None:
            self.min_rt = sys.float_info.min

        if self.max_rt is None:
            self.max_rt = sys.float_info.max

        if self.min_ook0 is None:
            self.min_ook0 = sys.float_info.min

        if self.max_ook0 is None:
            self.max_ook0 = sys.float_info.max

        if self.min_intensity is None:
            self.min_intensity = sys.float_info.min

        if self.max_intensity is None:
            self.max_intensity = sys.float_info.max

    def is_enveloped_by(self, other: 'ExclusionInterval'):

        if other.charge is not None and self.charge != other.charge:  # data must have correct charge
            return False

        if self.min_mass < other.min_mass or self.max_mass > other.max_mass:
            return False

        if self.min_rt < other.min_rt or self.max_rt > other.max_rt:
            return False

        if self.min_ook0 < other.min_ook0 or self.max_ook0 > other.max_ook0:
            return False

        if self.min_intensity < other.min_intensity or self.max_intensity > other.max_intensity:
            return False

        return True

    def dict(self):
        return {k: str(v) for k, v in asdict(self).items()}

    def is_point(self):
        if self.min_mass != self.max_mass:
            return False
        if self.min_rt != self.max_rt:
            return False
        if self.min_ook0 != self.max_ook0:
            return False
        if self.min_intensity != self.max_intensity:
            return False
        return True

    def is_valid(self):
        if self.min_mass > self.max_mass:
            return False
        if self.min_rt > self.max_rt:
            return False
        if self.min_ook0 > self.max_ook0:
            return False
        if self.min_intensity > self.max_intensity:
            return False
        return True


@dataclass()
class ExclusionPoint:
    """
    Represents a point in the excluded space. None values will be ignored.
    """
    charge: Union[int, None]
    mass: Union[float, None]
    rt: Union[float, None]
    ook0: Union[float, None]
    intensity: Union[float, None]

    def is_bounded_by(self, interval: ExclusionInterval) -> bool:
        """
        Check if point given by is_excluded() is within interval
        """
        if self.charge is not None and interval.charge is not None and self.charge != interval.charge:
            logging.debug(f'Charge oob: self {self.charge}, interval {interval.charge}')
            return False
        if self.mass is not None and (self.mass < interval.min_mass or self.mass >= interval.max_mass):
            logging.debug(f'mass oob: self {self.mass}, interval.min {interval.min_mass}, interval.max {interval.max_mass}')
            return False
        if self.rt is not None and (self.rt < interval.min_rt or self.rt >= interval.max_rt):
            logging.debug(f'rt oob: self {self.rt}, interval.min {interval.min_rt}, interval.max {interval.max_rt}')
            return False
        if self.ook0 is not None and (self.ook0 < interval.min_ook0 or self.ook0 >= interval.max_ook0):
            logging.debug(f'ook0 oob: self {self.ook0}, interval.min {interval.min_ook0}, interval.max {interval.max_ook0}')
            return False
        if self.intensity is not None and (self.intensity < interval.min_intensity or self.intensity >= interval.max_intensity):
            logging.debug(f'intensity intensity: self {self.intensity}, interval.min {interval.min_intensity}, interval.max {interval.max_intensity}')
            return False
        return True

    @staticmethod
    def generate_random(min_charge: int, max_charge: int, min_mass: float, max_mass: float, min_rt: float,
                        max_rt: float, min_ook0: float, max_ook0: float, min_intensity: float, max_intensity: float):
        charge = random.randint(min_charge, max_charge)
        mass = random.uniform(min_mass, max_mass)
        rt = random.uniform(min_rt, max_rt)
        ook0 = random.uniform(min_ook0, max_ook0)
        intensity = random.uniform(min_intensity, max_intensity)
        return ExclusionPoint(charge=charge, mass=mass, rt=rt, ook0=ook0, intensity=intensity)



@dataclass
class DynamicExclusionTolerance:
    exact_charge: bool
    mass_tolerance: Union[float, None]
    rt_tolerance: Union[float, None]
    ook0_tolerance: Union[float, None]
    intensity_tolerance: Union[float, None]

    def dict(self):
        return {k: str(v) for k, v in asdict(self).items()}

    @staticmethod
    def parse_exact_charge_str(exact_charge: str) -> bool:
        if type(exact_charge) == str:
            if str.lower(exact_charge) == 'true':
                exact_charge = True
            elif str.lower(exact_charge) == 'false':
                exact_charge = False
            else:
                raise IncorrectToleranceException(
                    f'exact_charge: {exact_charge} is of the wrong type: {type(exact_charge)}')
        elif type(exact_charge) != bool:
            raise IncorrectToleranceException(
                f'exact_charge: {exact_charge} is of the wrong type: {type(exact_charge)}')

        return exact_charge

    @staticmethod
    def parse_mass_tolerance_str(mass: str) -> Union[float, None]:
        if type(mass) == str:
            if mass == '':
                mass = None
            elif str.lower(mass) == 'none':
                mass = None
            else:
                try:
                    mass = float(mass)
                except ValueError:
                    raise IncorrectToleranceException(
                        f'mass tolerance: {mass} cannot be parsed into float.')
        elif type(mass) != float and type(mass) != int and mass != None:
            raise IncorrectToleranceException(
                f'mass tolerance: {mass} cannot be parsed into float.')

        return mass

    @staticmethod
    def parse_rt_tolerance_str(rt: str) -> Union[float, None]:
        if type(rt) == str:
            if rt == '':
                rt = None
            elif str.lower(rt) == 'none':
                rt = None
            else:
                try:
                    rt = float(rt)
                except ValueError:
                    raise IncorrectToleranceException(
                        f'rt tolerance: {rt} cannot be parsed into float.')
        elif type(rt) != float and type(rt) != int and rt != None:
            raise IncorrectToleranceException(
                f'rt tolerance: {rt} cannot be parsed into float.')
        return rt

    @staticmethod
    def parse_ook0_tolerance_str(ook0: str) -> Union[float, None]:
        if type(ook0) == str:
            if ook0 == '':
                ook0 = None
            elif str.lower(ook0) == 'none':
                ook0 = None
            else:
                try:
                    ook0 = float(ook0)
                except ValueError:
                    raise IncorrectToleranceException(
                        f'ook0 tolerance: {ook0} cannot be parsed into float.')
        elif type(ook0) != float and type(ook0) != int and ook0 != None:
            raise IncorrectToleranceException(
                f'ook0 tolerance: {ook0} cannot be parsed into float.')
        return ook0

    @staticmethod
    def parse_intensity_tolerance_str(intensity: str) -> Union[float, None]:
        if type(intensity) == str:
            if intensity == '':
                intensity = None
            elif str.lower(intensity) == 'none':
                intensity = None
            else:
                try:
                    intensity = float(intensity)
                except ValueError:
                    raise IncorrectToleranceException(
                        f'intensity tolerance: {intensity} cannot be parsed into float.')
        elif type(intensity) != float and type(intensity) != int and intensity != None:
            raise IncorrectToleranceException(
                f'intensity tolerance: {intensity} cannot be parsed into float.')
        return intensity

    @staticmethod
    def from_tolerance_dict(tolerance_dict: dict) -> 'DynamicExclusionTolerance':

        return DynamicExclusionTolerance(
            exact_charge=DynamicExclusionTolerance.parse_exact_charge_str(tolerance_dict.get('exact_charge')),
            mass_tolerance=DynamicExclusionTolerance.parse_mass_tolerance_str(tolerance_dict.get('mass')),
            rt_tolerance=DynamicExclusionTolerance.parse_rt_tolerance_str(tolerance_dict.get('rt')),
            ook0_tolerance=DynamicExclusionTolerance.parse_ook0_tolerance_str(tolerance_dict.get('ook0')),
            intensity_tolerance=DynamicExclusionTolerance.parse_intensity_tolerance_str(tolerance_dict.get('intensity'))
        )

    @staticmethod
    def from_strings(exact_charge: str, mass_tolerance: str, rt_tolerance: str, ook0_tolerance: str,
                  intensity_tolerance: str) -> 'DynamicExclusionTolerance':

        return DynamicExclusionTolerance(
            exact_charge=DynamicExclusionTolerance.parse_exact_charge_str(exact_charge),
            mass_tolerance=DynamicExclusionTolerance.parse_mass_tolerance_str(mass_tolerance),
            rt_tolerance=DynamicExclusionTolerance.parse_rt_tolerance_str(rt_tolerance),
            ook0_tolerance=DynamicExclusionTolerance.parse_ook0_tolerance_str(ook0_tolerance),
            intensity_tolerance=DynamicExclusionTolerance.parse_intensity_tolerance_str(intensity_tolerance)
        )

    def calculate_mass_bounds(self, mass: Union[float, None]):
        if self.mass_tolerance and mass:
            min_mass = mass - mass * self.mass_tolerance / 1_000_000
            max_mass = mass + mass * self.mass_tolerance / 1_000_000
            return min_mass, max_mass
        return None, None

    def calculate_rt_bounds(self, rt: Union[float, None]):
        if self.rt_tolerance and rt:
            min_rt = rt - self.rt_tolerance
            max_rt = rt + self.rt_tolerance
            return min_rt, max_rt
        return None, None

    def calculate_ook0_bounds(self, ook0: Union[float, None]):
        if self.ook0_tolerance and ook0:
            min_ook0 = ook0 - self.ook0_tolerance
            max_ook0 = ook0 + self.ook0_tolerance
            return min_ook0, max_ook0
        return None, None

    def calculate_intensity_bounds(self, intensity: Union[float, None]):
        if self.intensity_tolerance and intensity:
            min_intensity = intensity - self.intensity_tolerance
            max_intensity = intensity + self.intensity_tolerance
            return min_intensity, max_intensity
        return None, None

    def construct_interval(self, interval_id: str, exclusion_point: ExclusionPoint):

        charge = exclusion_point.charge
        if self.exact_charge is False:
            charge = None

        min_mass, max_mass = self.calculate_mass_bounds(exclusion_point.mass)
        min_rt, max_rt = self.calculate_rt_bounds(exclusion_point.rt)
        min_ook0, max_ook0 = self.calculate_ook0_bounds(exclusion_point.ook0)
        min_intensity, max_intensity = self.calculate_intensity_bounds(exclusion_point.intensity)

        return ExclusionInterval(id=interval_id, charge=charge, min_mass=min_mass,
                                 max_mass=max_mass, min_rt=min_rt, max_rt=max_rt, min_ook0=min_ook0,
                                 max_ook0=max_ook0, min_intensity=min_intensity, max_intensity=max_intensity)
