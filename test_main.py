import json

import exclusionms.components
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

example_oob_interval = '?interval_id=PEPTIDE&charge=1&min_mass=1002&max_mass=1001&min_rt=1000&max_rt=1001&' \
                       'min_ook0=1000&max_ook0=1001&min_intensity=1000&max_intensity=1001'
example_interval = '?interval_id=PEPTIDE&charge=1&min_mass=1000&max_mass=1001&min_rt=1000&max_rt=1001&min_ook0=1000' \
                   '&max_ook0=1001&min_intensity=1000&max_intensity=1001'
example_interval_dict = \
    {
        "id": "PEPTIDE",
        "charge": 1,
        "min_mass": 1000,
        "max_mass": 1001,
        "min_rt": 1000,
        "max_rt": 1001,
        "min_ook0": 1000,
        "max_ook0": 1001,
        "min_intensity": 1000,
        "max_intensity": 1001
    }

example_interval_with_none_dict = \
    {
        "id": "PEPTIDE",
        "charge": 1,
        "min_mass": 1000,
        "max_mass": 1001,
        "min_rt": 'None',
        "max_rt": 1001,
        "min_ook0": 'None',
        "max_ook0": 'None',
        "min_intensity": 1000,
        "max_intensity": 'None'
    }


example_oob_interval_dict = \
    {
        "id": "PEPTIDE",
        "charge": 1,
        "min_mass": 1002,
        "max_mass": 1001,
        "min_rt": 1000,
        "max_rt": 1001,
        "min_ook0": 1000,
        "max_ook0": 1001,
        "min_intensity": 1000,
        "max_intensity": 1001
    }

example_point = '?charge=1&mass=1000.5&rt=1000.5&ook0=1000.5&intensity=1000.5'
example_points = '?charge=1&mass=1000.5&rt=1000.5&ook0=1000.5&intensity=1000.5&charge=1&mass=1000.5&rt=1000.5' \
                 '&ook0=1000.5&intensity=1000.5'

example_point_dicts = [{"charge":1,
                       "mass":1000.5,
                       "rt":1000.5,
                       "ook0":1000.5,
                       "intensity": 1000.5
                       },
                       {"charge":1,
                       "mass":1000.5,
                       "rt":1000.5,
                       "ook0":1000.5,
                       "intensity": 1000.5
                       }]


def test_post_exclusion():
    response = client.delete("/exclusionms")
    assert response.status_code == 200


def test_post_exclusion_save():
    client.delete("/exclusionms")

    response = client.post("/exclusionms?save=True&exclusion_list_name=testing")
    assert response.status_code == 200

    response = client.delete("/exclusionms/file?exclusion_list_name=testing")
    assert response.status_code == 200


def test_post_exclusion_load():
    client.delete("/exclusionms")

    response = client.post("/exclusionms?save=True&exclusion_list_name=testing")
    assert response.status_code == 200

    response = client.post("/exclusionms?save=False&exclusion_list_name=testing")
    assert response.status_code == 200

    response = client.delete("/exclusionms/file?exclusion_list_name=testing")
    assert response.status_code == 200


def test_post_exclusion_load_fail():
    client.delete("/exclusionms")

    response = client.post("/exclusionms?save=False&exclusion_list_name=testing")
    assert response.status_code == 404


def test_delete_exclusion_save_fail():
    client.delete("/exclusionms")

    response = client.delete("/exclusionms/file?exclusion_list_name=testing")
    assert response.status_code == 404


def test_save_load():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)  # add interval
    assert response.status_code == 200

    response = client.post("/exclusionms?save=True&exclusion_list_name=testing")  # save
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")  # get intervals
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.post(f"/exclusionms/interval", json=example_interval_dict)  # add interval
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")  # get intervals
    assert response.status_code == 200
    assert response.json() == [example_interval_dict, example_interval_dict]

    response = client.post("/exclusionms?save=False&exclusion_list_name=testing")  # load
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")  # get intervals (should only be 1)
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]


def test_post_exclusion_interval():
    client.delete("/exclusionms")

    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.post(f"/exclusionms/interval", json=example_oob_interval_dict)
    assert response.status_code == 400

    response = client.post(f"/exclusionms/interval", json=example_interval_with_none_dict)
    assert response.status_code == 200


def test_get_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]


def test_get_exclusion_interval_by_id():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval?interval_id=PEPTIDE")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/interval?interval_id=PEPTIDE2")
    assert response.status_code == 200
    assert response.json() == []


def test_get_exclusion_interval_by_mass():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval?min_mass=1000&max_mass=1001")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/interval?max_mass=1001")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/interval?min_mass=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/interval?min_mass=1001&max_mass=1000")
    assert response.status_code == 400

    response = client.get(f"/exclusionms/interval?min_mass=1001")
    assert response.status_code == 200
    assert response.json() == []

    response = client.get(f"/exclusionms/interval?max_mass=1000")
    assert response.status_code == 200
    assert response.json() == []


def test_delete_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.delete(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    # Test if interval was deleted, plus add the interval back in
    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == []

    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200
    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.delete(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]


def test_get_multiple_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict, example_interval_dict]


def test_delete_multiple_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.delete(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == []

    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200


def test_get_point():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.get(f"/exclusionms/point{example_point}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?charge=1")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?mass=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?mass=1001")
    assert response.status_code == 200
    assert len(json.loads(response.content)) == 0

    response = client.get(f"/exclusionms/point?rt=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?rt=1001")
    assert response.status_code == 200
    assert len(json.loads(response.content)) == 0

    response = client.get(f"/exclusionms/point?ook0=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?ook0=1001")
    assert response.status_code == 200
    assert len(json.loads(response.content)) == 0

    response = client.get(f"/exclusionms/point?intensity=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?intensity=1001")
    assert response.status_code == 200
    assert len(json.loads(response.content)) == 0


def test_get_points():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval", json=example_interval_dict)
    assert response.status_code == 200

    response = client.post(f"/exclusionms/excluded_points", json=example_point_dicts)
    assert response.status_code == 200
    assert response.json() == [True, True]







