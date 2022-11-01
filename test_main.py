import time

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

example_point = '?charge=1&mass=1000.5&rt=1000.5&ook0=1000.5&intensity=1000.5'
example_points = '?charge=1&mass=1000.5&rt=1000.5&ook0=1000.5&intensity=1000.5&charge=1&mass=1000.5&rt=1000.5' \
                 '&ook0=1000.5&intensity=1000.5'


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
    response = client.post(f"/exclusionms/interval{example_interval}")  # add interval
    assert response.status_code == 200

    response = client.post("/exclusionms?save=True&exclusion_list_name=testing")  # save
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")  # get intervals
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.post(f"/exclusionms/interval{example_interval}")  # add interval
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

    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.post(f"/exclusionms/interval{example_oob_interval}")
    assert response.status_code == 400


def test_get_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]


def test_get_exclusion_interval_by_id():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval?interval_id=PEPTIDE")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/interval?interval_id=PEPTIDE2")
    assert response.status_code == 404


def test_get_exclusion_interval_by_mass():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
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
    assert response.status_code == 404

    response = client.get(f"/exclusionms/interval?max_mass=1000")
    assert response.status_code == 404


def test_delete_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.delete(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    # Test if interval was deleted, plus add the interval back in
    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 404
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.delete(f"/exclusionms/interval{example_oob_interval}")
    assert response.status_code == 400


def test_get_multiple_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict, example_interval_dict]


def test_delete_multiple_exclusion_interval():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.delete(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.get(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 404

    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200


def test_get_point():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
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
    assert response.status_code == 404

    response = client.get(f"/exclusionms/point?rt=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?rt=1001")
    assert response.status_code == 404

    response = client.get(f"/exclusionms/point?ook0=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?ook0=1001")
    assert response.status_code == 404

    response = client.get(f"/exclusionms/point?intensity=1000")
    assert response.status_code == 200
    assert response.json() == [example_interval_dict]

    response = client.get(f"/exclusionms/point?intensity=1001")
    assert response.status_code == 404


def test_get_points():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    response = client.get(f"/exclusionms/points{example_points}")
    assert response.status_code == 200
    assert response.json() == [True, True]


def test_add_interval_performance():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    start_time = time.time()
    for i in range(100):
        client.post(f"/exclusionms/interval{example_interval}")

    total_time = time.time() - start_time
    print(f'Interval Add time: {total_time}')
    assert total_time < 1


def test_get_interval_performance():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    start_time = time.time()
    for i in range(100):
        client.get(f"/exclusionms/interval{example_interval}")

    total_time = time.time() - start_time
    print(f'Interval Get time: {total_time}')
    assert total_time < 1


def test_head_interval_performance():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    start_time = time.time()
    for i in range(100):
        client.head(f"/exclusionms/interval{example_interval}")

    total_time = time.time() - start_time
    print(f'Interval Head time: {total_time}')
    assert total_time < 1


def test_get_point_performance():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    start_time = time.time()
    for i in range(100):
        client.get(f"/exclusionms/point{example_point}")

    total_time = time.time() - start_time
    print(f'Point Get time: {total_time}')
    assert total_time < 1


def test_head_point_performance():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    start_time = time.time()
    for i in range(100):
        client.head(f"/exclusionms/point{example_point}")

    total_time = time.time() - start_time
    print(f'Point Head time: {total_time}')
    assert total_time < 1


def test_get_points_performance():
    client.delete("/exclusionms")
    response = client.post(f"/exclusionms/interval{example_interval}")
    assert response.status_code == 200

    sub_str = '&charge=1&mass=1000.5&rt=1000.5&ook0=1000.5&intensity=1000.5'

    sub_strs = [sub_str] * 100
    sub_strs[0] = example_point
    points_query = ''.join(sub_strs)

    start_time = time.time()
    client.get(f"/exclusionms/points{points_query}")

    total_time = time.time() - start_time
    print(f'Point Heads time: {total_time}')
    assert total_time < 1
