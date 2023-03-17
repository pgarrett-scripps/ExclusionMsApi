# ExclusionMS Fast API

ExclusionMS is a FastAPI server for managing mass spectrometry exclusion lists. The server provides an API for adding, 
searching, and deleting intervals or points in the exclusion list. Additionally, it supports saving and loading 
exclusion lists as pickled objects, as well as managing offset values.

## How to Install

## Usage

### Local

```
git clone https://github.com/pgarrett-scripps/ExclusionMsApi
cd ExclusionMsApi
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Docker

```
docker run -d --name exclusion-ms-fastapi --restart unless-stopped -p 8000:8000 pgarrettscripps/exclusion-ms-api
```

### Docker Compose

```
cd ExclusionMsApi
docker-compose up -d
```

## Use an API client or a web browser to interact with the available API endpoints.

### API Endpoints

A more detailed and interactive endpoint tutorial can be found at http://exclusion_ms_ip:8000/docs 
(Default: http://127.0.0.1:8000/docs) after starting the server.

#### Exclusion List

- **/exclusionms/statistics (GET):** Retrieves statistics about the active exclusion list.
- **/exclusionms/file (GET):** Retrieves a list of saved file names in the data/pickles directory.
- **/exclusionms/save (POST):** Saves the active exclusion list as a pickled object with the given ID.
- **/exclusionms/load (POST):** Loads a pickled exclusion list with the given ID into the active exclusion list.
- **/exclusionms/clear (POST):** Clears all data from the active exclusion list.
- **/exclusionms/delete (POST):** Deletes the pickled exclusion list with the given ID.
- 
#### Intervals

- **/exclusionms/intervals/search (POST):** Searches the active exclusion list for intervals that intersect with the given exclusion intervals.
- **/exclusionms/intervals (POST):** Adds the given exclusion intervals to the active exclusion list.
- **/exclusionms/intervals (DELETE):** Deletes the given exclusion intervals from the active exclusion list.
- 
#### Points

- **/exclusionms/points/search (POST):** Searches the active exclusion list for intervals containing the specified ExclusionPoint objects.
- **/exclusionms/points/exclusion_search (POST):** Checks whether each specified ExclusionPoint is excluded by the active exclusion list.

#### Offset
- **/exclusionms/offset (GET):** Returns the current offset values.
- **/exclusionms/offset (POST):** Updates the offset values.

## What are Exclusion Intervals and Points?

ExclusionMS operates in a multidimensional exclusion space defined by the following ionic properties: charge, mass, 
retention time, ion mobility (ook0), and intensity.

You can set any value to null. For minimum/maximum bounds, this sets the min bound to -/+ infinity. For single values
(charge in Exclusion Intervals or any property in Exclusion Points), this will cause that dimension to be excluded.

## Exclusion Interval json format:
```
  {
    "interval_id": string,
    "charge": int | null,
    "min_mass": float | null,
    "max_mass": float | null,
    "min_rt": float | null,
    "max_rt": float | null,
    "min_ook0": float | null,
    "max_ook0": float | null,
    "min_intensity": float | null,
    "max_intensity": float | null
  }
  ```
## Example json message:
  ```
  {
    "interval_id": 'ID1',
    "charge": null,
    "min_mass": 1000,
    "max_mass": 1001,
    "min_rt": 300,
    "max_rt": 350,
    "min_ook0": null,
    "max_ook0": 1.2,
    "min_intensity": 10000,
    "max_intensity": null
  }
```

## Exclusion Point json format:

```
  {
    "charge": int | null,
    "mass": float | null,
    "rt": float | null,
    "ook0": float | null,
    "intensity": float | null
  }
```

## Example json message (contained within above interval):

```
  {
    "charge": null,
    "mass": 1000.5,
    "rt": 330,
    "ook0": 0.5,
    "intensity": 50000
  }
```

## Contact
For any questions or issues, please contact:

[Patrick Garrett](pgarrett@scripps.edu)
