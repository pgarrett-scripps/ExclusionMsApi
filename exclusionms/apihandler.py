import json
from typing import List

import requests

from .components import ExclusionPoint, ExclusionInterval
from .exceptions import UnexpectedStatusCodeException
from .queryfactory import make_save_query, make_load_query, make_stats_query, \
    make_exclusion_interval_query, make_clear_query, make_exclusion_points_query


def clear_active_exclusion_list(exclusion_api_ip: str):
    response = requests.delete(make_clear_query(exclusion_api_ip))
    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)


def load_active_exclusion_list(exclusion_api_ip: str, exid: str):
    response = requests.post(make_load_query(exclusion_api_ip, exid))
    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)


def save_active_exclusion_list(exclusion_api_ip: str, exid: str):
    response = requests.post(make_save_query(exclusion_api_ip, exid))
    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)


def get_active_exclusion_list_stats(exclusion_api_ip: str) -> List[str]:
    response = requests.get(make_stats_query(exclusion_api_ip))
    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)

    else:
        return json.loads(response.content)['active_exclusion_list']


def get_exclusion_list_files(exclusion_api_ip: str) -> List[str]:
    response = requests.get(make_stats_query(exclusion_api_ip))
    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)

    else:
        return json.loads(response.content)['files']


def add_exclusion_interval_query(exclusion_api_ip: str, exclusion_interval: ExclusionInterval) -> None:
    query = make_exclusion_interval_query(exclusion_api_ip=exclusion_api_ip,
                                          exclusion_interval=exclusion_interval)

    response = requests.post(query)

    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)


def get_excluded_points(exclusion_api_ip: str, exclusion_points: List[ExclusionPoint]):
    query = make_exclusion_points_query(exclusion_api_ip=exclusion_api_ip,
                                        exclusion_points=exclusion_points)

    response = requests.get(query)

    if response.status_code != 200:
        raise UnexpectedStatusCodeException(response.content)

    return json.loads(response.content)
