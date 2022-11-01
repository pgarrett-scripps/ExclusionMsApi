import logging
import os
from typing import List

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks, FastAPI

from constants import DATA_FOLDER, PROCESS_CANDIDATES_FILE
from exclusionms.components import ExclusionInterval, ExclusionPoint, DynamicExclusionTolerance
from exclusionms.db import MassIntervalTree as ExclusionList
from utils import convert_int, convert_float

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)

app = FastAPI()

active_exclusion_list = ExclusionList()


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
    return {'files': saved_files_names, 'active_exclusion_list':active_exclusion_list.stats()}


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


@app.get("/exclusionms/interval", response_model=List[ExclusionInterval], status_code=200)
async def get_interval(interval_id: str | None = None, charge: int | None = None, min_mass: float | None = None,
                       max_mass: float | None = None, min_rt: float | None = None, max_rt: float | None = None,
                       min_ook0: float | None = None, max_ook0: float | None = None, min_intensity: float | None = None,
                       max_intensity: float | None = None):
    exclusion_interval = ExclusionInterval(id=interval_id, charge=charge, min_mass=min_mass, max_mass=max_mass,
                                           min_rt=min_rt, max_rt=max_rt, min_ook0=min_ook0, max_ook0=max_ook0,
                                           min_intensity=min_intensity, max_intensity=max_intensity)
    exclusion_interval.convert_none()

    if not exclusion_interval.is_valid():
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds.")

    intervals = active_exclusion_list.query_by_interval(exclusion_interval)

    if not intervals:
        raise HTTPException(status_code=404, detail=f"No intervals found")

    return intervals


@app.head("/exclusionms/interval", status_code=200)
async def head_interval(interval_id: str | None = None, charge: int | None = None, min_mass: float | None = None,
                        max_mass: float | None = None, min_rt: float | None = None, max_rt: float | None = None,
                        min_ook0: float | None = None, max_ook0: float | None = None,
                        min_intensity: float | None = None, max_intensity: float | None = None):
    exclusion_interval = ExclusionInterval(id=interval_id, charge=charge, min_mass=min_mass, max_mass=max_mass,
                                           min_rt=min_rt, max_rt=max_rt, min_ook0=min_ook0, max_ook0=max_ook0,
                                           min_intensity=min_intensity, max_intensity=max_intensity)
    exclusion_interval.convert_none()
    if not exclusion_interval.is_valid():
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds.")

    intervals = active_exclusion_list.query_by_interval(exclusion_interval)

    if not intervals:
        raise HTTPException(status_code=404, detail=f"No intervals found")


def _add_exclusion_interval(exclusion_interval: ExclusionInterval):
    exclusion_interval.convert_none()
    active_exclusion_list.add(exclusion_interval)


@app.post("/exclusionms/interval", status_code=200)
async def add_interval(background_tasks: BackgroundTasks,
                       interval_id: str | None = None, charge: int | None = None, min_mass: float | None = None,
                       max_mass: float | None = None, min_rt: float | None = None, max_rt: float | None = None,
                       min_ook0: float | None = None, max_ook0: float | None = None, min_intensity: float | None = None,
                       max_intensity: float | None = None):
    exclusion_interval = ExclusionInterval(id=interval_id, charge=charge, min_mass=min_mass, max_mass=max_mass,
                                           min_rt=min_rt, max_rt=max_rt, min_ook0=min_ook0, max_ook0=max_ook0,
                                           min_intensity=min_intensity, max_intensity=max_intensity)
    exclusion_interval.convert_none()

    if not exclusion_interval.is_valid() or interval_id is None:
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds.")

    background_tasks.add_task(active_exclusion_list.add, ex_interval=exclusion_interval)


# TODO: Return deleted Items?
@app.delete("/exclusionms/interval", status_code=200)
async def remove_interval(background_tasks: BackgroundTasks,
                          interval_id: str | None = None, charge: int | None = None, min_mass: float | None = None,
                          max_mass: float | None = None, min_rt: float | None = None, max_rt: float | None = None,
                          min_ook0: float | None = None, max_ook0: float | None = None,
                          min_intensity: float | None = None, max_intensity: float | None = None):
    exclusion_interval = ExclusionInterval(id=interval_id, charge=charge, min_mass=min_mass, max_mass=max_mass,
                                           min_rt=min_rt, max_rt=max_rt, min_ook0=min_ook0, max_ook0=max_ook0,
                                           min_intensity=min_intensity, max_intensity=max_intensity)
    exclusion_interval.convert_none()

    if not exclusion_interval.is_valid():
        raise HTTPException(status_code=400, detail=f"exclusion interval invalid. Check min/max bounds.")

    background_tasks.add_task(active_exclusion_list.remove, ex_interval=exclusion_interval)


@app.get("/exclusionms/point", response_model=List[ExclusionInterval], status_code=200)
async def get_point(charge: int | None = None, mass: float | None = None,
                    rt: float | None = None, ook0: float | None = None, intensity: float | None = None):
    exclusion_point = ExclusionPoint(charge=charge, mass=mass, rt=rt, ook0=ook0, intensity=intensity)
    intervals = active_exclusion_list.query_by_point(exclusion_point)

    if not intervals:
        raise HTTPException(status_code=404, detail=f"No intervals found")

    return intervals


@app.head("/exclusionms/point", status_code=200)
async def head_point(charge: int | None = None, mass: float | None = None,
                     rt: float | None = None, ook0: float | None = None, intensity: float | None = None):
    exclusion_point = ExclusionPoint(charge=charge, mass=mass, rt=rt, ook0=ook0, intensity=intensity)
    intervals = active_exclusion_list.query_by_point(exclusion_point)

    if not intervals:
        raise HTTPException(status_code=404, detail=f"No intervals found")


@app.get("/exclusionms/points", response_model=List[bool], status_code=200)
async def get_points(charge: List[int | str] = Query(), mass: List[int | str] = Query(), rt: List[int | str] = Query(),
                     ook0: List[int | str] = Query(), intensity: List[int | str] = Query()):
    if len({len(i) for i in [charge, mass, rt, ook0, intensity]}) != 1:
        raise HTTPException(status_code=400, detail=f"lists are not the same size")

    points = []
    for point_values in zip(charge, mass, rt, ook0, intensity):
        point = ExclusionPoint(charge=convert_int(point_values[0]), mass=convert_float(point_values[1]),
                               rt=convert_float(point_values[2]), ook0=convert_float(point_values[3]),
                               intensity=convert_float(point_values[4]))
        points.append(point)

    exclusions = []
    for point in points:
        exclusions.append(active_exclusion_list.is_excluded(point))
    return exclusions


@app.get("/exclusionms/stats", status_code=200)
async def get_statistics():
    return active_exclusion_list.stats()


@app.get("/exclusionms/random/interval", status_code=200)
async def add_random_intervals(n: int, min_charge: int, max_charge: int, min_mass: float, max_mass: float, min_rt: float,
                               max_rt: float, min_ook0: float, max_ook0: float, min_intensity: float,
                               max_intensity: float, use_exact_charge: bool, mass_tolerance: float | None = None,
                               rt_tolerance: float | None = None, ook0_tolerance: float | None = None,
                               intensity_tolerance: float | None = None):

    tolerance = DynamicExclusionTolerance(exact_charge=use_exact_charge, mass_tolerance=mass_tolerance,
                                           rt_tolerance=rt_tolerance, ook0_tolerance=ook0_tolerance,
                                           intensity_tolerance=intensity_tolerance)



    for i in range(n):
        random_exclusion_point = ExclusionPoint.generate_random(min_charge=min_charge, max_charge=max_charge,
                                                                min_mass=min_mass, max_mass=max_mass,
                                                                min_rt=min_rt, max_rt=max_rt,
                                                                min_ook0=min_ook0, max_ook0=max_ook0,
                                                                min_intensity=min_intensity, max_intensity=max_intensity)
        random_interval = tolerance.construct_interval(interval_id='testing', exclusion_point=random_exclusion_point)
        random_interval.convert_none()
        active_exclusion_list.add(random_interval)
