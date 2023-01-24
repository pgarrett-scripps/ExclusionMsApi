import logging
import os
from typing import List, Dict

from fastapi import HTTPException, FastAPI

from constants import DATA_FOLDER
from exclusionms.components import ExclusionInterval, ExclusionPoint
from exclusionms.db import MassIntervalTree as ExclusionList
from utils import Offset

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)

app = FastAPI()

active_exclusion_list = ExclusionList()
offset = Offset()


def get_pickle_path(exclusion_list_name: str) -> str:
    return os.path.join(DATA_FOLDER, exclusion_list_name + '.pkl')


@app.get("/exclusionms/statistics", status_code=200)
async def get_statistics() -> Dict:
    _log.info(f'Exclusion List Statistics')
    return active_exclusion_list.stats()


@app.get("/exclusionms/file", status_code=200)
async def get_files() -> List[str]:
    _log.info(f'Exclusion List Files')
    saved_files = os.listdir(DATA_FOLDER)
    saved_files_names = [''.join(f.split('.')[:-1]) for f in saved_files]
    return saved_files_names


@app.post("/exclusionms/save", status_code=200)
async def save(exid: str):
    pickle_path = get_pickle_path(exid)

    _log.info(f'Save Exclusion List')
    if os.path.exists(pickle_path):
        _log.warning(f'{pickle_path} already exists. Overriding.')

    try:
        active_exclusion_list.save(pickle_path)
    except Exception as e:
        _log.error(f'Error when saving exclusion list: {e}')
        raise HTTPException(status_code=500, detail='Error saving active exclusion list.')


@app.post("/exclusionms/load", status_code=200)
async def load(exid: str):
    pickle_path = get_pickle_path(exid)

    _log.info(f'Load Exclusion List')
    if not os.path.exists(pickle_path):
        raise HTTPException(status_code=404, detail=f"exclusion list with name: {exid} not found.")

    try:
        active_exclusion_list.load(pickle_path)
    except Exception as e:
        _log.error(f'Exception when loading exclusion list: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail='Error loading active exclusion list.')


@app.post("/exclusionms/clear", status_code=200)
async def clear() -> int:
    _log.info(f'Delete Active Exclusion List')
    num_intervals_cleared = len(active_exclusion_list)
    active_exclusion_list.clear()
    return num_intervals_cleared


@app.post("/exclusionms/delete", status_code=200)
async def delete(exid: str):
    _log.info(f'Delete Exclusion List Save')
    pickle_path = get_pickle_path(exid)

    if not os.path.exists(pickle_path):
        raise HTTPException(status_code=404, detail=f"exclusion list with name: {exid} not found.")

    try:
        os.remove(pickle_path)
    except Exception as e:
        _log.error(f'Error when deleting exclusion list: {e}')
        raise HTTPException(status_code=500, detail='Error deleting exclusion list.')


@app.post("/exclusionms/intervals/search", response_model=List[List[ExclusionInterval]], status_code=200)
async def search_intervals(exclusion_intervals: List[ExclusionInterval]):
    for exclusion_interval in exclusion_intervals:
        if not exclusion_interval.is_valid():
            raise HTTPException(status_code=400,
                                detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")

    return [active_exclusion_list.query_by_interval(exclusion_interval) for exclusion_interval in exclusion_intervals]


@app.post("/exclusionms/intervals", response_model=None, status_code=200)
async def add_intervals(exclusion_intervals: List[ExclusionInterval]):
    for exclusion_interval in exclusion_intervals:
        if not exclusion_interval.is_valid():
            raise HTTPException(status_code=400,
                                detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")
    _ = [active_exclusion_list.add(exclusion_interval) for exclusion_interval in exclusion_intervals]


@app.delete("/exclusionms/intervals", response_model=List[List[ExclusionInterval]], status_code=200)
async def delete_intervals(exclusion_intervals: List[ExclusionInterval]):
    for exclusion_interval in exclusion_intervals:
        if not exclusion_interval.is_valid():
            raise HTTPException(status_code=400,
                                detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")
    return [active_exclusion_list.remove(exclusion_interval) for exclusion_interval in exclusion_intervals]


def apply_offset(point: ExclusionPoint, offset: Offset):
    if point.mass:
        point.mass += offset.mass
    if point.rt:
        point.rt += offset.rt
    if point.ook0:
        point.ook0 += offset.ook0
    if point.intensity:
        point.intensity += offset.intensity


@app.post("/exclusionms/points/search", response_model=List[List[ExclusionInterval]], status_code=200)
async def search_points(exclusion_points: list[ExclusionPoint]):
    for point in exclusion_points:
        apply_offset(point, offset)

    return [list(active_exclusion_list.query_by_point(point)) for point in exclusion_points]


@app.post("/exclusionms/points/exclusion_search", response_model=List[bool], status_code=200)
async def exclusion_search_points(exclusion_points: list[ExclusionPoint]):
    for point in exclusion_points:
        apply_offset(point, offset)

    return [active_exclusion_list.is_excluded(point) for point in exclusion_points]


@app.get("/exclusionms/offset", status_code=200)
async def get_offset() -> Offset:
    _log.info(f'Get offset')
    return offset


@app.post("/exclusionms/offset", status_code=200)
async def update_offset(mass: float = 0, rt: float = 0, ook0: float = 0, intensity: float = 0):
    _log.info(f'Update offset')
    offset.mass = mass
    offset.rt = rt
    offset.ook0 = ook0
    offset.intensity = intensity
