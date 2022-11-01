import traceback
from dataclasses import dataclass, asdict

from kafka import KafkaConsumer
from schema_registry.client import SchemaRegistryClient
from schema_registry.serializers import MessageSerializer

from .components import ExclusionInterval

import logging
from threading import Thread

#TODO: Remove defaults
@dataclass
class ExclusionListConfig:
    mass_tolerance: float = 50
    rt_tolerance: float = 100
    ook0_tolerance: float = 0.05
    intensity_tolerance: float = 0.5
    score_thresholds: float = 2.0
    kafka_ip: str = '172.29.227.247:9092'
    schema_ip: str = 'http://172.29.227.247:8083'
    topic: str = 'psm_prolucid'
    group_id: str = 'exclusion_list'
    uid: str = '6cfa7ad1-7c70-4146-8a7c-f4d5051c8e24_1666810322'

    def dict(self):
        return {k: str(v) for k, v in asdict(self).items()}


class ExclusionListWorker(Thread):
    """
    This class provides the implementation for the worker thread and can be tested separately.
    """

    def __init__(self, exclusion_list, ex_config):
        """
        Constructor for feedback worker implementation class
        :param create_consumer: Factory to create search feedback message consumer. Might throw.
        :psm_tree: psm_tree obj (db for psms)
        :uid: The current acquisition UID
        """
        super().__init__(daemon=True)
        self._exclusion_list = exclusion_list
        self._ex_config = ex_config

    def run(self):
        """
        Consumes psm_exclusion topic to add/remove intervals from the exclusionms list
        """
        #logging.basicConfig(filename="log.txt", level=logging.DEBUG)
        #logging.debug("Debug logging test...")
        consumer = create_consumer(schema_ip=self._ex_config.schema_ip,
                                         kafka_ip=self._ex_config.kafka_ip,
                                         topic=self._ex_config.topic,
                                         group_id=self._ex_config.group_id)
        try:
            for message in consumer:
                if self._ex_config.uid == message.key:
                    psm = message.value

                    if psm['mono_mz'] is None or psm['mono_mz'] == 0:
                        continue

                    if psm['charge'] is None or psm['charge'] == 0:
                        continue

                    if psm['rt'] is None or psm['rt'] == 0:
                        continue

                    if psm['ooK0'] is None or psm['ooK0'] == 0:
                        continue

                    ms2_id = psm['ms2_id']
                    mass = psm['mono_mz'] * psm['charge'] - psm['charge'] * 1.00727647
                    ex_interval = ExclusionInterval(id=f'{self._ex_config.uid}_{ms2_id}',
                                                    charge=psm['charge'],
                                                    min_mass=mass - mass*self._ex_config.mass_tolerance/1_000_000,
                                                    max_mass=mass + mass*self._ex_config.mass_tolerance/1_000_000,
                                                    min_rt=psm['rt'] - self._ex_config.rt_tolerance,
                                                    max_rt = psm['rt'] + self._ex_config.rt_tolerance,
                                                    min_ook0 = psm['ooK0'] - psm['ooK0']*self._ex_config.ook0_tolerance,
                                                    max_ook0 = psm['ooK0'] + psm['ooK0']*self._ex_config.ook0_tolerance,
                                                    min_intensity=None,
                                                    max_intensity=None)

                    self._exclusion_list.add(ex_interval)
        except Exception as e:
            logging.error("Error consuming messages!!!", e)
            logging.error(traceback.format_exc())


def create_consumer(schema_ip, kafka_ip, topic, group_id):
    """ factory function to create consumer. Encapsulates kafka dependency"""
    print(schema_ip, kafka_ip, topic, group_id)
    schema_client = SchemaRegistryClient(url=schema_ip)
    serializer = MessageSerializer(schema_client)

    return KafkaConsumer(topic,
                         group_id=group_id,
                         bootstrap_servers=[kafka_ip],
                         key_deserializer=lambda m: m.decode('utf-8') if m is not None else None,
                         value_deserializer=lambda m: serializer.decode_message(m) if m is not None else None,
                         auto_offset_reset='earliest',
                         enable_auto_commit=False)
