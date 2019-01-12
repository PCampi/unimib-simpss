"""Main file, use it for trying things out."""

import os

import mocks
from simpss import mqtt_kafka_producer

if __name__ == "__main__":
    # MQTT config
    mqtt_config = {
        'client-id': 'py',
        'address': 'localhost',
        'port': 1883,
        'transport': 'tcp',
        'topic': 'simpss',
        'qos': 2,
        'max-inflight': 100,
    }

    datapath = '/Users/pietro/Documents/Uni/Large_Scale_Data_Management/cassandra/test_data/log.txt'
    delay = float(os.environ.get("SENSOR_DELAY", '10'))
    mocks.sensor.run_sensor(datapath, topic='simpss', publish_every=delay)
