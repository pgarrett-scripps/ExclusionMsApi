import requests
import json
import time


def make_interval_query(interval_id: str | None, charge: int | None, min_mass: float | None, max_mass: float | None,
                        min_rt: float | None, max_rt: float | None, min_ook0: float | None, max_ook0: float | None,
                        min_intensity: float | None, max_intensity: float | None):
    interval_query = ''
    if interval_id:
        interval_query += f'&interval_id={interval_id}'
    if charge:
        interval_query += f'&charge={charge}'
    if min_mass:
        interval_query += f'&min_mass={min_mass}'
    if max_mass:
        interval_query += f'&max_mass={max_mass}'
    if min_rt:
        interval_query += f'&min_rt={min_rt}'
    if max_rt:
        interval_query += f'&max_rt={max_rt}'
    if min_ook0:
        interval_query += f'&min_ook0={min_ook0}'
    if max_ook0:
        interval_query += f'&max_ook0={max_ook0}'
    if min_intensity:
        interval_query += f'&min_intensity={min_intensity}'
    if max_intensity:
        interval_query += f'&max_intensity={max_intensity}'

    if interval_query:
        interval_query = '?' + interval_query[1:]

    return interval_query


def process_candidates(self, candidates, make_candidate, enable_individual_collision_energies):
    paser_exclusion_api_ip = '127.0.0.1:8000'
    with self._lock:
        if self._is_initialized is False or len(candidates) == 0:
            return

        def is_candidate_valid(candidate) -> bool:
            if candidate.precursor.monoisotopic_mz is None or candidate.precursor.monoisotopic_mz == 0:
                return False
            if candidate.precursor.charge is None or candidate.precursor.charge == 0:
                return False
            if candidate.one_over_k0 is None or candidate.one_over_k0 == 0:
                return False
            return True

        def calculate_mass(mz, charge):
            return mz * charge - charge * 1.00727647

        start_time = time.time()
        for i in sorted([i for i, candidate in enumerate(candidates) if not is_candidate_valid(candidate)],
                        reverse=True):
            candidates.pop(i)

        if len(candidates) == 0:
            return

        charges = ''.join([f'&charge={candidate.precursor.charge}' for candidate in candidates])
        masses = ''.join(
            [f'&mass={calculate_mass(candidate.precursor.monoisotopic_mz, candidate.precursor.charge)}' for candidate in
             candidates])
        rts = ''.join([f'&rt={float(self._ms1_analysis_time)}' for candidate in candidates])
        ook0s = ''.join([f'&ook0={candidate.one_over_k0}' for candidate in candidates])
        ints = ''.join([f'&intensity={None}' for candidate in candidates])
        exclusion_points_query = charges + masses + rts + ook0s + ints
        exclusion_points_query = '?' + exclusion_points_query[1:]

        response = requests.get(f'http://{paser_exclusion_api_ip}/exclusionlist/points{exclusion_points_query}')
        data = response.text
        exclusion_flags = json.loads(data)

        for i in sorted([i for i, flag in enumerate(exclusion_flags) if flag], reverse=True):
            candidates.pop(i)

        """for candidate in candidates:
            mass = calculate_mass(candidate.precursor.monoisotopic_mz, candidate.precursor.charge)
            response = requests.post(f'http://127.0.0.1:8000/exclusion/interval?id=TEST&min_mass={mass - mass*50/1_000_000}&max_mass={mass + mass*50/1_000_000}')"""

        candidates = [c for c, f in zip(candidates, exclusion_flags) if not f]
        _log.info(f"starting candidates: {len(exclusion_flags)}, remaining candidates: {len(candidates)}")
        _log.info("--- %s process_candidates time (seconds) ---" % round((time.time() - start_time), 4))