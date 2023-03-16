# ExclusionMS Fast API

ExclusionMS is a FastAPI server for managing mass spectrometry exclusion lists. The server provides an API for adding, searching, and deleting intervals or points in the exclusion list. Additionally, it supports saving and loading exclusion lists as pickled objects, as well as managing offset values.

## How to Install
```
git clone https://github.com/pgarrett-scripps/ExclusionMsApi
cd ExclusionMsApi
pip install -r requirements.txt
```
## Usage
Run the server using an ASGI server like Uvicorn or Hypercorn.
```
uvicorn main:app --reload --port 8000
```

## Use an API client or a web browser to interact with the available API endpoints.

### API Endpoints

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

## Contact
For any questions or issues, please contact:

[Patrick Garrett](pgarrett@scripps.edu)
