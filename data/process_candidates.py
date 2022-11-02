from __future__ import annotations

import logging
import time
from threading import Lock

from .exclusionms.apihandler import load_active_exclusion_list, save_active_exclusion_list, get_exclusion_list_files, \
    clear_active_exclusion_list, add_exclusion_interval_query, get_excluded_points
from .exclusionms.components import DynamicExclusionTolerance, IncorrectToleranceException, ExclusionPoint
from .paserproducer.ddaproducer import DdaPasefProducer
from .paserproducer.prddataclasses import MsMsInfo
from .paserproducer.sampleinfo import has_key_pac_qualifier
from .paserproducer.serializer import ms2_pasef_spectrum_to_avro, calib_to_avro, extract_exp_name

_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)


def create_dda_pasef_plugin(paser_key_dict, config, requests_head, create_producer,
                            create_pac_worker, create_feedback_worker):
    return DdaPasefPlugin(paser_key_dict, config, requests_head, create_producer,
                          create_pac_worker, create_feedback_worker)


"""
------------------  Exclusion-MS calculate_mass Start ------------------ 
"""
def calculate_mass(mz: float, charge: int) -> float:
    return mz * charge - charge * 1.00727647
"""
------------------  Exclusion-MS calculate_mass Start ------------------ 
"""

class DdaPasefPlugin:
    """
    PASER (Parallel database Search Engine in Realtime).
    Utilizes ProLucid's GPU workspaces to search fragmented peptide spectra in real time. MsMs spectra are sent
    via a Kafka producer to a Kafka broker asynchronously to avoid blocking acquisition.
    This plugin starts a thread - pac thread. Within the thread blocking rest calls are made to paser-head for
    evaluation of pac qualifiers
    """

    def __init__(self, paser_key_dict, config, requests_head,
                 create_producer, create_pac_worker, create_feedback_worker):
        """
        The Plugin constructor is called from the timsEngine.exe when a method with reference to this plugin
        is loaded.
        the producer is not initialized in the constructor because the constructor is called with every method
        load event. This would create a new search result in IP2 every time a paser-method is loaded.
        :param config: object with configuration parameters
        """
        self._lock = Lock()
        # self._is_initialized is set to false the plugin basically does nothing and cannot affect acquisition.
        # It is set to false in the following cases
        # - no Hystar SampleInfo is available
        # - no acquisition was started
        # - a critical error occurred, e.g. connection to PaSER broke, or PaSER sends an internal critical error
        self._is_initialized = False
        self._reference_time = 0.0
        self._ms1_analysis_time = 0.0
        self._has_qualifier = None
        self._previous_ms2_info = MsMsInfo(0, range(-1, -1))
        self._current_ms2_info = MsMsInfo(0, range(-1, -1))
        self._ms2_spectrum_id = 0
        self._current_mob_trafo = None
        self._requests_head = requests_head
        self._config = config
        self._has_qualifier = has_key_pac_qualifier(paser_key_dict)

        _log.info(f"PaSER key {paser_key_dict}")
        self._producer = DdaPasefProducer(self._config, create_producer, self._uid)

        # create PAC worker, returns a queue where to push pac events to.
        self._pac_queue = create_pac_worker(config)


        """
        ------------------  Exclusion-MS Init Start ------------------ 
        """
        self._uid = paser_key_dict['uid']
        self._exid = None
        self._dynamic_tolerance = None
        if paser_key_dict.get('exlist'):
            self._exid = str(paser_key_dict.get('exlist').get('exid'))
            if paser_key_dict.get('exlist').get('dynamic') is True and paser_key_dict.get('exlist').get('tolerance'):
                try:
                    self._dynamic_tolerance = DynamicExclusionTolerance.from_tolerance_dict(
                        paser_key_dict.get('exlist').get('tolerance'))
                except IncorrectToleranceException as e:
                    _log.error(f'IncorrectToleranceException: {e}. Disabling dynamic exclusion')

        _log.info(f'exid: {self._exid}, dynamic tolerance: {self._dynamic_tolerance}')
        """
        ------------------ Exclusion-MS Init End ------------------ 
        """

    def analysis_started(self, analysis_directory, reference_time):
        _log.info(f"starting analysis, {analysis_directory}, {reference_time}")

        with self._lock:
            try:
                self._reference_time = reference_time
                self._previous_ms2_info = MsMsInfo(0, range(-1, -1))
                self._current_ms2_info = MsMsInfo(0, range(-1, -1))
                self._ms2_spectrum_id = 0
                # send start call to paser-head
                self._requests_head.start(self._uid, extract_exp_name(analysis_directory))
                self._is_initialized = True
                _log.debug("paser-plugin started")
            except Exception as e:
                _log.error(f"initialization of paser failed {e}")
                self._is_initialized = False

        """
        ------------------  Exclusion-MS analysis_started Start ------------------ 
        """
        try:
            if self._exid is not None:
                available_exclusion_lists = get_exclusion_list_files(self._config.exclusion_api.ip)
                _log.info(f'available exclusion lists: {available_exclusion_lists}')
                if self._exid not in available_exclusion_lists:
                    _log.info(f"Exclusion list with ID: {self._exid} not found. Making new list.")
                    clear_active_exclusion_list(self._config.exclusion_api.ip)
                    save_active_exclusion_list(self._config.exclusion_api.ip, self._exid)
                _log.info(f"Loading Exclusion list with ID: {self._exid}")
                load_active_exclusion_list(self._config.exclusion_api.ip, self._exid)
        except Exception as ex:
            _log.error(f"Error Loading ExclusionList {ex}. Disabling exclusion list for run.", exc_info=True)
            self._exid = None
        """
        ------------------ Exclusion-MS analysis_started End ------------------ 
        """

        _log.info("analysis started")

    def analysis_stopped(self):
        """
        This function is called when acquisition stops. Messages on the fly are flushed.
        There is a timeout of 30 seconds configured. So the flush-call might through a
        Kafka time-out exception. In any case exceptions from _send_calibration and flush need to be caught so
        that we can ensure that a) paser-head's stop REST service is called and b) stop-messages for paser_control
        topic are send to shutdown the workflow. For that purpose 3 try-except blocks are used.
        """
        _log.info("stopping analysis")
        with self._lock:
            # we might have the error case that acquisition was not dda-PASEF but a different
            # scan mode. In that case nothing was send and error message should be written
            # to the log
            if not self._ms1_analysis_time > 0.0:
                _log.error("No data send, this is most likely not a dda-PASEF acquisition ...")

            try:
                # send PAC trigger just if qualifier available
                if self._has_qualifier and self._pac_queue is not None:
                    if self._pac_queue.empty():
                        _log.info(f"send PAC request to {self._uid}")
                        self._pac_queue.put_nowait(self._uid)
                    else:
                        _log.info("a PAC message is currently processed")
            except Exception as ex:
                _log.error(f"flushing or pac failed when stopping {ex}")

            try:
                # now make sure stop messages are send to paser_control
                self._producer.send_status_stopped()
            except Exception as ex:
                _log.error(f"send stop messages to paser_control failed {ex}")

            """
            ------------------  Exclusion-MS analysis_stopped Start ------------------ 
            """
            try:
                if self._exid is not None:
                    save_active_exclusion_list(self._config.exclusion_api.ip, self._exid)
                    _log.info(f"Saved Exclusion List with name: {self._exid}")
            except Exception as ex:
                _log.error(f"Error Saving Exclusion List: {ex}")
                self._exid = None
            """
            ------------------  Exclusion-MS analysis_stopped End ------------------ 
            """

            try:
                # inform paser-head the analysis was stopped with data flushed
                self._requests_head.stop(self._uid)
            except Exception as ex:
                _log.error(f"send stop status to paser-head failed {ex}")
            finally:
                self._is_initialized = False
                _log.info("analysis stopped")

    def _get_analysis_time(self, monotonic_time):
        """Return current analysis time, or -1 if not acquiring data.

        Given the monotonic time of some data measured by the engine, the analysis time is exactly
        the time stamp that would be assigned in a TDF raw-data file (if that data were recorded).
        """
        if self._is_initialized is False:
            return -1
        return monotonic_time - self._reference_time

    def find_precursors(self, frame_peaks, transformators, ms1_monotonic_time, ms1_token):
        with self._lock:
            if self._is_initialized is False:
                return

            try:
                # we start a new cycle, copy current msms_info to the previous
                self._previous_ms2_info.ms1_frame_id = self._current_ms2_info.ms1_frame_id
                # a deep copy of range
                self._previous_ms2_info.precursor_range = self._current_ms2_info.precursor_range
                # increment ms1 frame id and invalidate precursor range
                self._current_ms2_info.ms1_frame_id += 1
                self._current_ms2_info.precursor_range = range(-1, -1)
                _log.debug(f"ms1 frame id: {self._current_ms2_info.ms1_frame_id}")

                self._ms1_analysis_time = self._get_analysis_time(ms1_monotonic_time)
                _log.debug(f"ms1 frame time {self._ms1_analysis_time}")
                self._current_mob_trafo = transformators.tims_transformator
            except Exception as ex:
                self._is_initialized = False
                _log.error(f"exception in find_precursors, uninitializing paser-plugin {ex}")

    def schedule_candidates(self, candidates, settings):
        _log.info(f'schedule_candidates got {len(candidates)} candidates')
        with self._lock:
            # If not currently not acquiring data: Skip
            if self._is_initialized is False or len(candidates) == 0:
                return

            try:
                min_id = min(candidates, key=lambda c: c.precursor.engine_id).precursor.engine_id
                max_id = max(candidates, key=lambda c: c.precursor.engine_id).precursor.engine_id
                self._current_ms2_info.precursor_range = range(min_id, max_id + 1)  # range end is exclusive

                _log.debug(
                    f"sched, prev: {self._previous_ms2_info.ms1_frame_id}, {self._previous_ms2_info.precursor_range}")
                _log.debug(
                    f"sched, curr: {self._current_ms2_info.ms1_frame_id}, {self._current_ms2_info.precursor_range}")
            except Exception as ex:
                self._is_initialized = False
                _log.error(f"exception schedule_candidates, uninitializing paser-plugin {ex}")

    """
    ------------------  Exclusion-MS process_candidates Start ------------------ 
    """
    def process_candidates(self, candidates, make_candidate, enable_individual_collision_energies):

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

            start_time = time.time()
            for i in sorted([i for i, candidate in enumerate(candidates) if not is_candidate_valid(candidate)],
                            reverse=True):
                candidates.pop(i)

            if len(candidates) == 0 or self._exid is None:
                return

            exclusion_points = []
            num_starting_candidates = len(candidates)
            for candidate in candidates:
                exclusion_points.append(ExclusionPoint(charge=candidate.precursor.charge,
                                                       mass=calculate_mass(candidate.precursor.monoisotopic_mz,
                                                                           candidate.precursor.charge),
                                                       rt=self._ms1_analysis_time,
                                                       ook0=candidate.one_over_k0,
                                                       intensity=candidate.precursor.intensity))

            try:
                exclusion_flags = get_excluded_points(self._config.exclusion_api.ip,
                                                      exclusion_points=exclusion_points)

                for i in sorted([i for i, flag in enumerate(exclusion_flags) if flag], reverse=True):
                    candidates.pop(i)


            except Exception as ex:
                _log.error(f'exception when excluding candidates: {ex}')
            finally:
                _log.info(f"starting candidates: {num_starting_candidates}, remaining candidates: {len(candidates)}")
                _log.info("--- %s process_candidates time (seconds) ---" % round((time.time() - start_time), 4))
    """
    ------------------  Exclusion-MS process_candidates End ------------------ 
    """

    def new_msms_spectra(self, spectra, ms2_monotonic_time):
        with self._lock:
            if self._is_initialized is False or len(spectra) == 0:
                return
            try:
                min_id = min(spectra, key=lambda s: s.precursor.engine_id).precursor.engine_id
                max_id = max(spectra, key=lambda s: s.precursor.engine_id).precursor.engine_id
                _log.debug(f"msms spectra: ({min_id}, {max_id})")

                for spec in spectra:
                    self._ms2_spectrum_id += 1
                    if spec.precursor.engine_id in self._previous_ms2_info.precursor_range:
                        ms1_frame_id = self._previous_ms2_info.ms1_frame_id
                        _log.debug(
                            f"spec {spec.precursor.engine_id}, prev cycle {self._previous_ms2_info.ms1_frame_id}")
                    elif spec.precursor.engine_id in self._current_ms2_info.precursor_range:
                        ms1_frame_id = self._current_ms2_info.ms1_frame_id
                        _log.debug(f"spec {spec.precursor.engine_id}, curr cycle {self._current_ms2_info.ms1_frame_id}")
                    else:
                        _log.warning(f"invalid msms spectrum id {spec.precursor.engine_id}")
                        continue

                    # Currently, we ignore ms2 spectra where precursor charge could not be detected.
                    # In that case charge is 0, and we ignore that ms2 spectrum.
                    if spec.precursor.charge is None:
                        continue

                    """
                    ------------------  Exclusion-MS new_msms_spectra Start ------------------ 
                    """
                    if self._dynamic_tolerance is not None and self._exid is not None:
                        self._exclude_ms2_spec(spec, self._ms2_spectrum_id, self._ms1_analysis_time)
                    """
                    ------------------  Exclusion-MS new_msms_spectra End ------------------ 
                    """

                    # Note, currently we ignore ms2 spectra where precursor charge and monoisotopic m/z could not be
                    # detected. So we do not have to worry about spectrum.precursor.monoisotopic_mz being None, here
                    ms2_record = self._map_ms2_spec(spec, ms1_frame_id, self._ms2_spectrum_id, self._ms1_analysis_time)
                    self._producer.publish_ms2_pasef_spectrum(ms2_record)
            except Exception as ex:
                self._is_initialized = False
                _log.error(f"exception publishing ms2 spectra, uninitializing paser-plugin {ex}")

    def _map_ms2_spec(self, spectrum, ms1_frame_id, ms2_spectrum_id, time_):
        precursor_mobility = 0.0
        if self._current_mob_trafo is not None:
            precursor_mobility = self._current_mob_trafo.scan_number_to_one_over_k0(spectrum.precursor.scan_number)
        else:
            _log.error("mobility transformator invalid")

        # mz values and intensity values are encoded as little endian ordered bytes here
        # note that .tobytes() also works on an empty array
        return ms2_pasef_spectrum_to_avro(ms2_id=ms2_spectrum_id, parent_id=ms1_frame_id, rt=time_,
                                          ooK0=precursor_mobility, mono_mz=spectrum.precursor.monoisotopic_mz,
                                          intensity=spectrum.precursor.intensity, charge=spectrum.precursor.charge,
                                          mz_arr=spectrum.mz_values, intensity_arr=spectrum.area_values)

    """
    ------------------  Exclusion-MS _exclude_ms2_spec Start ------------------ 
    """
    def _exclude_ms2_spec(self, spectrum, ms2_spectrum_id, time_):
        precursor_mobility = 0.0
        if self._current_mob_trafo is not None:
            precursor_mobility = self._current_mob_trafo.scan_number_to_one_over_k0(spectrum.precursor.scan_number)
        else:
            _log.error("mobility transformator invalid")

        mz = spectrum.precursor.monoisotopic_mz
        charge = spectrum.precursor.charge
        ook0 = precursor_mobility[0]
        rt = time_
        intensity = spectrum.precursor.intensity

        if None in [mz, charge, ook0, rt, intensity] or 0 in [mz, charge, ook0, rt, intensity]:
            return

        interval_id = f'{self._uid}_{ms2_spectrum_id}'
        mass = calculate_mass(mz, charge)

        exclusion_point = ExclusionPoint(charge=charge, mass=mass, rt=rt, ook0=ook0, intensity=intensity)
        exclusion_interval = self._dynamic_tolerance.construct_interval(interval_id=interval_id,
                                                                        exclusion_point=exclusion_point)
        try:
            add_exclusion_interval_query(exclusion_api_ip=self._config.exclusion_api.ip,
                                         exclusion_interval=exclusion_interval)
        except Exception as ex:
            _log.error(f'Problem posing new dynamic interval {ex}')

    """
    ------------------  Exclusion-MS _exclude_ms2_spec End ------------------ 
    """
