from typing import List, Union

from .components import ExclusionInterval, ExclusionPoint


def make_clear_query(exclusion_api_ip: str):
    return f'{exclusion_api_ip}/exclusionms'


def make_save_query(exclusion_api_ip: str, exid: str):
    return f'{exclusion_api_ip}/exclusionms?save=True&exclusion_list_name={exid}'


def make_load_query(exclusion_api_ip: str, exid: str):
    return f'{exclusion_api_ip}/exclusionms?save=False&exclusion_list_name={exid}'


def make_stats_query(exclusion_api_ip: str):
    return f'{exclusion_api_ip}/exclusionms'


def make_exclusion_interval_query(exclusion_api_ip: str, exclusion_interval: ExclusionInterval) -> str:
    interval_query = ''
    if exclusion_interval.id:
        interval_query += f'&interval_id={exclusion_interval.id}'
    if exclusion_interval.charge:
        interval_query += f'&charge={exclusion_interval.charge}'
    if exclusion_interval.min_mass:
        interval_query += f'&min_mass={exclusion_interval.min_mass}'
    if exclusion_interval.max_mass:
        interval_query += f'&max_mass={exclusion_interval.max_mass}'
    if exclusion_interval.min_rt:
        interval_query += f'&min_rt={exclusion_interval.min_rt}'
    if exclusion_interval.max_rt:
        interval_query += f'&max_rt={exclusion_interval.max_rt}'
    if exclusion_interval.min_ook0:
        interval_query += f'&min_ook0={exclusion_interval.min_ook0}'
    if exclusion_interval.max_ook0:
        interval_query += f'&max_ook0={exclusion_interval.max_ook0}'
    if exclusion_interval.min_intensity:
        interval_query += f'&min_intensity={exclusion_interval.min_intensity}'
    if exclusion_interval.max_intensity:
        interval_query += f'&max_intensity={exclusion_interval.max_intensity}'

    if interval_query:
        interval_query = '?' + interval_query[1:]

    add_interval_api_str = f'{exclusion_api_ip}/exclusionms/interval{interval_query}'

    return add_interval_api_str


def make_exclusion_points_query(exclusion_api_ip: str, exclusion_points: List[ExclusionPoint]):
    charges_sub_query = ''.join([f'&charge={point.charge}' for point in exclusion_points])
    masses_sub_query = ''.join([f'&mass={point.mass}' for point in exclusion_points])
    rts_sub_query = ''.join([f'&rt={point.rt}' for point in exclusion_points])
    ook0s_sub_query = ''.join([f'&ook0={point.ook0}' for point in exclusion_points])
    intensities_sub_query = ''.join([f'&intensity={point.intensity}' for point in exclusion_points])

    exclusion_points_query = charges_sub_query + masses_sub_query + rts_sub_query + ook0s_sub_query + intensities_sub_query
    exclusion_points_query = '?' + exclusion_points_query[1:]

    query_points_api_str = f'{exclusion_api_ip}/exclusionms/points{exclusion_points_query}'

    return query_points_api_str
