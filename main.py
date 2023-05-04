import logging
from logging.handlers import RotatingFileHandler

from typing import List, Dict

from fastapi import HTTPException, FastAPI, BackgroundTasks

from constants import DATA_FOLDER
from exclusionms.components import ExclusionInterval, ExclusionPoint
from exclusionms.db import MassIntervalTree as ExclusionList
from utils import Offset

import asyncio

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import json
import os

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)

max_file_size = 10 * 1024 * 1024  # 10 MB
backup_count = 5  # Number of backup log files to keep

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("request_history.log", maxBytes=max_file_size, backupCount=backup_count),
        logging.StreamHandler()
    ],
)

logger = logging.getLogger(__name__)
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get request data
        request_data = {
            'method': request.method,
            'url': str(request.url),
            'headers': dict(request.headers),
        }

        # Record the start time
        start_time = time.time()

        # Get response data
        response: Response = await call_next(request)

        # Calculate the time taken to process the request
        time_taken = time.time() - start_time

        response_data = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'client_ip': request.client.host,
        }

        # Combine request, response data, and timings
        log_entry = {
            'request': request_data,
            'response': response_data,
            'time_taken': time_taken,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(start_time)),
        }

        # Write the log entry to a file
        log_file = 'api_calls.log'
        mode = 'a' if os.path.exists(log_file) else 'w'
        with open(log_file, mode) as f:
            f.write(json.dumps(log_entry) + "\n")

        return response


app = FastAPI(
    title="ExclusionMS",
    description='ExclusionMS FAST API Server',
    version="0.0.1",
    contact={
        "name": "Patrick Garrett",
        "email": "pgarrett@scripps.edu",
    }
)

app.add_middleware(LoggingMiddleware)

tags_metadata = [
    {
        "name": "Exclusion List",
        "description": "API calls for active exclusion list",
    },
    {
        "name": "Intervals",
        "description": "API calls Exclusion Intervals",
    },
    {
        "name": "Points",
        "description": "API calls for Exclusion Points",
    },
    {
        "name": "Offset",
        "description": "API calls for updating offsets",
    },
]

active_exclusion_list = ExclusionList()
offset = Offset()
lock = asyncio.Lock()

def get_pickle_path(exclusion_list_name: str) -> str:
    return os.path.join(DATA_FOLDER, exclusion_list_name + '.pkl')


@app.get("/exclusionms/statistics", status_code=200, tags=['Exclusion List'])
async def get_statistics() -> Dict:
    """
    Retrieves statistics about the active exclusion list. If successful, returns a status code of 200.

    Returns:
        A dictionary containing the following keys and values:
            - 'len': the number of exclusion intervals in the active exclusion list.
            - 'id_table_len': the total number of entries in the ID dictionary used by the exclusion list.
            - 'class': a string representation of the class of the active exclusion list.
    """
    _log.info(f'Exclusion List Statistics')
    return active_exclusion_list.stats()


@app.get("/exclusionms/file", status_code=200, tags=['Exclusion List'])
async def get_files() -> List[str]:
    """
    Retrieves a list of saved file names in the data/pickles directory. If successful, returns a status code of 200.

    Returns:
        A list of strings, where each string represents the name of a saved file in the data/pickles directory.
        The file extension is removed from each filename.
    """
    _log.info(f'Exclusion List Files')
    saved_files = os.listdir(DATA_FOLDER)
    saved_files_names = [''.join(f.split('.')[:-1]) for f in saved_files]
    return saved_files_names


@app.post("/exclusionms/save", status_code=200, tags=['Exclusion List'])
async def save(exid: str):
    """
    Saves the active exclusion list as a pickled object with the given ID. If successful, returns a status code of 200.

    Args:
        exid: A string representing the ID to use for the saved exclusion list.

    Returns:
        None.

    Raises:
        HTTPException with a status code of 500: If there is an error when saving the active exclusion list.

    Notes:
        The saved file will be located in the data/pickles directory with the name '<exid>.pkl'.
        If a file with the same name already exists, it will be overwritten without warning.
    """
    pickle_path = get_pickle_path(exid)

    _log.info(f'Save Exclusion List')
    if os.path.exists(pickle_path):
        _log.warning(f'{pickle_path} already exists. Overriding.')

    try:
        active_exclusion_list.save(pickle_path)
    except Exception as e:
        _log.error(f'Error when saving exclusion list: {e}')
        raise HTTPException(status_code=500, detail='Error saving active exclusion list.')


@app.post("/exclusionms/load", status_code=200, tags=['Exclusion List'])
async def load(exid: str):
    """
    Loads a pickled exclusion list with the given ID into the active exclusion list. If successful, returns a status code of 200.

    Args:
        exid: A string representing the ID of the exclusion list to load.

    Returns:
        None.

    Raises:
        HTTPException: If the exclusion list with the given ID is not found (status code 404) or there is an error when loading it (status code 500).

    Notes:
        The file to load is located in the data/pickles directory with the name '<exid>.pkl'.
    """
    pickle_path = get_pickle_path(exid)

    _log.info(f'Load Exclusion List')
    if not os.path.exists(pickle_path):
        raise HTTPException(status_code=404, detail=f"exclusion list with name: {exid} not found.")

    try:
        active_exclusion_list.load(pickle_path)
    except Exception as e:
        _log.error(f'Exception when loading exclusion list: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail='Error loading active exclusion list.')


@app.post("/exclusionms/clear", status_code=200, tags=['Exclusion List'])
async def clear() -> int:
    """
    Clears all data from the active exclusion list. If successful, returns a status code of 200.

    Returns:
        An integer representing the number of exclusion intervals that were cleared.
    """
    _log.info(f'Delete Active Exclusion List')
    num_intervals_cleared = len(active_exclusion_list)
    active_exclusion_list.clear()
    return num_intervals_cleared


@app.post("/exclusionms/delete", status_code=200, tags=['Exclusion List'])
async def delete(exid: str):
    """
    Deletes the pickled exclusion list with the given ID. If successful, returns a status code of 200.

    Args:
        exid: A string representing the ID of the exclusion list to delete.

    Returns:
        None.

    Raises:
        HTTPException 404: If the exclusion list with the given ID is not found.
        HTTPException 500: If there is an error when deleting the

    Notes:
        The file to delete is located in the data/pickles directory with the name '<exid>.pkl'.
    """
    _log.info(f'Delete Exclusion List Save')
    pickle_path = get_pickle_path(exid)

    if not os.path.exists(pickle_path):
        raise HTTPException(status_code=404, detail=f"exclusion list with name: {exid} not found.")

    try:
        os.remove(pickle_path)
    except Exception as e:
        _log.error(f'Error when deleting exclusion list: {e}')
        raise HTTPException(status_code=500, detail='Error deleting exclusion list.')


@app.post("/exclusionms/intervals/search", response_model=List[List[ExclusionInterval]], status_code=200,
          tags=["Intervals"])
async def search_intervals(exclusion_intervals: List[ExclusionInterval]):
    """
    Searches the active exclusion list for intervals that intersect with the given exclusion intervals.
    If successful, returns a status code of 200.

    Args:
        exclusion_intervals: A list of ExclusionInterval objects representing the intervals to search for.

    Returns:
        A list of lists of ExclusionInterval objects representing the intervals in the active exclusion list that
        intersect with each exclusion interval in the input list.

    Raises:
        HTTPException 400: If any of the input exclusion intervals is invalid (i.e. its minimum bound is greater than
        its maximum bound)

    Notes:
        The function acquires a lock on the active exclusion list before querying it to ensure thread safety.
    """
    for exclusion_interval in exclusion_intervals:
        if not exclusion_interval.is_valid():
            raise HTTPException(status_code=400,
                                detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")

    intervals = []
    for exclusion_interval in exclusion_intervals:
        async with lock:
            intervals.append(active_exclusion_list.query_by_interval(exclusion_interval))

    return intervals


async def process_intervals(exclusion_intervals: List[ExclusionInterval]):
    for interval in exclusion_intervals:
        async with lock:
            active_exclusion_list.add(interval)


@app.post("/exclusionms/intervals", response_model=None, status_code=200, tags=["Intervals"])
async def add_intervals(exclusion_intervals: List[ExclusionInterval], background_tasks: BackgroundTasks):
    """
    Adds the given exclusion intervals to the active exclusion list. If successful, returns a status code of 200.

    Args:
        exclusion_intervals: A list of ExclusionInterval objects representing the intervals to add.

    Returns:
        None.

    Raises:
        HTTPException 400: If any of the input exclusion intervals is invalid (i.e. its minimum bound is greater than
        its maximum bound)

    Notes:
        The function acquires a lock on the active exclusion list before adding intervals to ensure thread safety.
    """

    for exclusion_interval in exclusion_intervals:
        if not exclusion_interval.is_valid():
            raise HTTPException(status_code=400,
                                detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")

    background_tasks.add_task(process_intervals, exclusion_intervals)


@app.delete("/exclusionms/intervals", response_model=List[List[ExclusionInterval]], status_code=200, tags=["Intervals"])
async def delete_intervals(exclusion_intervals: List[ExclusionInterval]):
    """
    Deletes the given exclusion intervals from the active exclusion list. If successful, returns a status code of 200.

    Args:
        exclusion_intervals: A list of ExclusionInterval objects representing the intervals to delete.

    Returns:
        A list of lists of ExclusionInterval objects representing the intervals that were deleted from the active
        exclusion list for each input exclusion interval.

    Raises:
        HTTPException 400: If any of the input exclusion intervals is invalid (i.e. its minimum bound is greater than
        its maximum bound)

    Notes:
        The function acquires a lock on the active exclusion list before deleting intervals to ensure thread safety.
    """
    for exclusion_interval in exclusion_intervals:
        if not exclusion_interval.is_valid():
            raise HTTPException(status_code=400,
                                detail=f"exclusion interval invalid. Check min/max bounds. {exclusion_interval}")

    deleted_intervals = []
    for exclusion_interval in exclusion_intervals:
        async with lock:
            deleted_intervals.append(active_exclusion_list.remove(exclusion_interval))

    return deleted_intervals


def apply_offset(point: ExclusionPoint, offset: Offset):
    """
    Applies the given offset to the specified ExclusionPoint object.

    Args:
        point: An ExclusionPoint object representing the point to apply the offset to.
        offset: An Offset object representing the offset to apply to the ExclusionPoint object.

    Returns:
        None.

    Notes:
        The function modifies the ExclusionPoint object in place. If any of the offset values are None, they are not
        applied to the ExclusionPoint object.
    """
    if point.mass:
        point.mass += offset.mass
    if point.rt:
        point.rt += offset.rt
    if point.ook0:
        point.ook0 += offset.ook0
    if point.intensity:
        point.intensity += offset.intensity


@app.post("/exclusionms/points/search", response_model=List[List[ExclusionInterval]], status_code=200, tags=["Points"])
async def search_points(exclusion_points: list[ExclusionPoint]):
    """
    Searches the active exclusion list for intervals containing the specified ExclusionPoint objects.
    If successful, returns a status code of 200.

    Args:
        exclusion_points: A list of ExclusionPoint objects representing the points to search for.

    Returns:
        A list of lists of ExclusionInterval objects representing the intervals that contain each input ExclusionPoint.

    Notes:
        The function applies any offset values specified in the ExclusionPoint objects before searching the exclusion list.
        It acquires a lock on the active exclusion list before performing the search to ensure thread safety.
    """
    for point in exclusion_points:
        apply_offset(point, offset)

    async with lock:
        return [list(active_exclusion_list.query_by_point(point)) for point in exclusion_points]


@app.post("/exclusionms/points/exclusion_search", response_model=List[bool], status_code=200, tags=["Points"])
async def exclusion_search_points(exclusion_points: list[ExclusionPoint]):
    """
    Checks whether each specified ExclusionPoint is excluded by the active exclusion list.
    If successful, returns a status code of 200.

    Args:
        exclusion_points: A list of ExclusionPoint objects representing the points to check.

    Returns:
        A list of boolean values representing whether each input ExclusionPoint is excluded by the active exclusion list.

    Notes:
        The function applies any offset values specified in the ExclusionPoint objects before checking exclusion.
    """
    for point in exclusion_points:
        apply_offset(point, offset)

    async with lock:
        return [active_exclusion_list.is_excluded(point) for point in exclusion_points]


@app.get("/exclusionms/offset", status_code=200, tags=['Offset'])
async def get_offset() -> Offset:
    """
    Returns the current offset values. If successful, returns a status code of 200.

    Returns:
        An Offset object representing the current offset values.
    """
    _log.info(f'Get offset')
    return offset


@app.post("/exclusionms/offset", status_code=200, tags=['Offset'])
async def update_offset(mass: float = 0, rt: float = 0, ook0: float = 0, intensity: float = 0):
    """
    Updates the offset values. If successful, returns a status code of 200.

    Args:
        mass: A float representing the mass offset value (default: 0).
        rt: A float representing the RT offset value (default: 0).
        ook0: A float representing the OOK0 offset value (default: 0).
        intensity: A float representing the intensity offset value (default: 0).

    Notes:
        The function updates the global `offset` object with the specified offset values.
    """
    _log.info(f'Update offset')
    offset.mass = mass
    offset.rt = rt
    offset.ook0 = ook0
    offset.intensity = intensity


@app.get('/logs/entries')
async def get_log_entries(num_entries: int = 500):
    log_file = 'api_calls.log'
    entries = []

    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()

        # Get the last num_entries lines (log entries)
        last_n_lines = lines[-num_entries:]

        for line in last_n_lines:
            try:
                entry = json.loads(line.strip())
                entries.append(entry)
            except json.JSONDecodeError:
                pass

    return entries
