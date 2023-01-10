from __future__ import annotations

import logging
import os
from typing import List

from fastapi import HTTPException, FastAPI
from fastapi.responses import FileResponse

from constants import DATA_FOLDER, PROCESS_CANDIDATES_FILE
from exclusionms.components import ExclusionIntervalMsg, ExclusionPointMsg, ExclusionPoint
from exclusionms.db import MassIntervalTree as ExclusionList
from utils import Offset

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)

app = FastAPI()

active_exclusion_list = ExclusionList()
offset = Offset()


def get_pickle_path(exclusion_list_name: str) -> str:
    return os.path.join(DATA_FOLDER, exclusion_list_name + '.pkl')


@app.get("/", status_code=200)
async def get_process_candidates_file():
    return FileResponse(path=PROCESS_CANDIDATES_FILE, filename=PROCESS_CANDIDATES_FILE, media_type='text')


# TODO: add exclusion list names to statistics
@app.get("/exclusionms", status_code=200)
async def get_exclusion_list_statistics():
    _log.info(f'Exclusion List Statistics')
    saved_files = os.listdir(DATA_FOLDER)
    saved_files_names = [''.join(f.split('.')[:-1]) for f in saved_files]
    return {'files': saved_files_names, 'active_exclusion_list': active_exclusion_list.stats(), 'Offsets:': offset}


# TODO: Add in merge command
@app.post("/exclusionms", status_code=200)
async def save_load_active_exclusion_list(save: bool, exclusion_list_name: str):
    pickle_path = get_pickle_path(exclusion_list_name)
    _log.info(f'pickle_path: {pickle_path}')

    if save:
        _log.info(f'Save Exclusion List')
        if os.path.exists(pickle_path):
            _log.warning(f'{pickle_path} already exists. Overriding.')

        try:
            active_exclusion_list.save(pickle_path)
        except Exception as e:
            _log.error(f'Error when saving exclusion list: {e}')
            raise HTTPException(status_code=500, detail='Error saving active exclusion list.')

    else:
        _log.info(f'Load Exclusion List')
        if not os.path.exists(pickle_path):
            raise HTTPException(status_code=404, detail=f"exclusion list with name: {exclusion_list_name} not found.")

        try:
            active_exclusion_list.load(pickle_path)
        except Exception as e:
            _log.error(f'Exception when loading exclusion list: {e}', exc_info=True)
            raise HTTPException(status_code=500, detail='Error loading active exclusion list.')


@app.delete("/exclusionms", status_code=200)
async def clear_active_exclusion_list():
    _log.info(f'Delete Active Exclusion List')
    active_exclusion_list.clear()


@app.delete("/exclusionms/file", status_code=200)
async def delete_exclusion_list_save(exclusion_list_name: str):
    _log.info(f'Delete Exclusion List Save')
    pickle_path = get_pickle_path(exclusion_list_name)

    if not os.path.exists(pickle_path):
        raise HTTPException(status_code=404, detail=f"exclusion list with name: {exclusion_list_name} not found.")

    try:
        os.remove(pickle_path)
    except Exception as e:
        _log.error(f'Error when deleting exclusion list: {e}')
        raise HTTPException(status_code=500, detail='Error deleting exclusion list.')


@app.get("/exclusionms/file", status_code=200)
async def download_exclusion_list_save(exclusion_list_name: str):
    _log.info(f'Download Exclusion List')
    pickle_path = get_pickle_path(exclusion_list_name)

    if not os.path.exists(pickle_path):
        raise HTTPException(status_code=404, detail=f"exclusion list with name: {exclusion_list_name} not found.")

    return FileResponse(path=pickle_path)


@app.post("/exclusionms/file", status_code=200)
async def upload_exclusion_list_save(file):
    _log.info(f'Upload Exclusion List')
    return


@app.get("/exclusionms/interval", response_model=List[ExclusionIntervalMsg], status_code=200)
async def get_interval(interval_id: str, charge: str, min_mass: str, max_mass: str, min_rt: str, max_rt: str,
                       min_ook0: str, max_ook0: str, min_intensity: str, max_intensity: str):
    exclusion_interval = ExclusionIntervalMsg(interval_id=interval_id, charge=charge, min_mass=min_mass, max_mass=max_mass,
                                              min_rt=min_rt, max_rt=max_rt, min_ook0=min_ook0, max_ook0=max_ook0,
                                              min_intensity=min_intensity, max_intensity=max_intensity)\
        .to_exclusion_interval()

    if not exclusion_interval.is_valid():
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")

    intervals = active_exclusion_list.query_by_interval(exclusion_interval)
    interval_msgs = [ExclusionIntervalMsg.from_exclusion_interval(interval) for interval in intervals]
    return interval_msgs


@app.post("/exclusionms/interval", status_code=200)
async def add_interval(exclusion_interval_msg: ExclusionIntervalMsg):
    exclusion_interval = ExclusionIntervalMsg.to_exclusion_interval(exclusion_interval_msg)

    if not exclusion_interval.is_valid() or exclusion_interval.interval_id is None:
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")

    active_exclusion_list.add(ex_interval=exclusion_interval)


@app.post("/exclusionms/intervals", status_code=200)
async def add_interval(exclusion_interval_msgs: List[ExclusionIntervalMsg]):
    for exclusion_interval_msg in exclusion_interval_msgs:
        exclusion_interval = ExclusionIntervalMsg.to_exclusion_interval(exclusion_interval_msg)

        if not exclusion_interval.is_valid() or exclusion_interval.interval_id is None:
            raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds.")

        active_exclusion_list.add(ex_interval=exclusion_interval)


@app.delete("/exclusionms/interval", response_model=List[ExclusionIntervalMsg], status_code=200)
async def remove_interval(exclusion_interval_msg: ExclusionIntervalMsg):
    exclusion_interval = ExclusionIntervalMsg.to_exclusion_interval(exclusion_interval_msg)
    if not exclusion_interval.is_valid():
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds.")
    intervals = active_exclusion_list.remove(exclusion_interval)
    interval_msgs = [ExclusionIntervalMsg.from_exclusion_interval(interval) for interval in intervals]
    return interval_msgs


@app.get("/exclusionms/point", response_model=List[ExclusionIntervalMsg], status_code=200)
async def get_point(charge: str, mass: str, rt: str, ook0: str, intensity: str):
    exclusion_point = ExclusionPointMsg(charge=charge, mass=mass, rt=rt, ook0=ook0,
                                        intensity=intensity).to_exclusion_point()
    exclusion_intervals = active_exclusion_list.query_by_point(exclusion_point)
    return [ExclusionIntervalMsg.from_exclusion_interval(interval) for interval in exclusion_intervals]


def apply_offset(point: ExclusionPoint, offset: Offset):
    if point.mass:
        point.mass += offset.mass
    if point.rt:
        point.rt += offset.rt
    if point.ook0:
        point.ook0 += offset.ook0
    if point.intensity:
        point.intensity += offset.intensity


@app.post("/exclusionms/excluded_points", response_model=List[bool], status_code=200)
async def get_points(exclusion_point_msgs: list[ExclusionPointMsg]):
    exclusion_points = [msg.to_exclusion_point() for msg in exclusion_point_msgs]

    for point in exclusion_points:
        apply_offset(point, offset)

    return [active_exclusion_list.is_excluded(point) for point in exclusion_points]


@app.get("/exclusionms/stats", status_code=200)
async def get_statistics():
    return active_exclusion_list.stats()


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
