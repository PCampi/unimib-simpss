"""File linking the MQTT broker to the Kafka cluster."""

import os
from typing import Dict

import pandas as pd

from simpss.producers import MqttKafkaProducer
import utils


def main():
    """Main function."""
    logger = utils.get_logger()
    logger.info("setting up MQTT")
    # MQTT config
    qos = int(os.environ.get("MQTT_QOS", 2))
    username = str(os.environ.get("MQTT_USER", 'simpss'))
    password = str(os.environ.get("MQTT_PASSWORD", 'simpss24112017'))
    client_id = str(os.environ.get("MQTT_CLIENT_ID", 'prod1'))
    mqtt_address = str(os.environ.get("MQTT_ADDRESS", 'localhost'))
    mqtt_topic = str(os.environ.get("MQTT_TOPIC", 'SIMPSS/+/DATA'))
    mqtt_max_inflight = int(os.environ.get("MQTT_MAX_INFLIGHT", 100))
    mqtt_payload_key = str(os.environ.get("MQTT_PAYLOAD_KEY", 'id'))
    mqtt_config = {
        'user': username,
        'password': password,
        'client-id': client_id,
        'address': mqtt_address,
        'port': 1883,
        'transport': 'tcp',
        'topic': mqtt_topic,
        'qos': qos,
        'max-inflight': mqtt_max_inflight,
        'payload-key': mqtt_payload_key,
        'timeout': 1.0,  # optional, default is 1.0
    }

    # KAFKA config
    logger.info("setting up KAFKA")
    bootstrap_servers = str(
        os.environ.get("KAFKA_BOOTSTRAP_SERVERS", 'localhost:9092'))
    kafka_timeout_ms = int(os.environ.get("KAFKA_TIMEOUS_MS", 6000))
    kafka_client_id = str(os.environ.get("KAFKA_CLIENT_ID", 'k-prod-1'))
    kafka_max_inflight = int(os.environ.get("KAFKA_MAX_INFLIGHT", 100))
    kafka_linger_ms = int(os.environ.get("KAFKA_LINGER_MS", 1))
    kafka_group_id = str(os.environ.get("KAFKA_GROUP_ID", '1'))
    kk_config = {
        'bootstrap.servers': bootstrap_servers,
        'session.timeout.ms': kafka_timeout_ms,
        'group.id': kafka_group_id,
        'client.id': kafka_client_id,
        'max.in.flight': kafka_max_inflight,
        'linger.ms': kafka_linger_ms,  # 0.001 seconds
    }

    logger.info("reading sensor file")
    sensor_groups = utils.read_sensor_group_mapping(
        os.path.join(os.getcwd(), 'sensor_group.csv'))
    logger.info(f"configuration read: {str(sensor_groups)}")

    bonzo = MqttKafkaProducer(mqtt_config,
                              kk_config,
                              sensor_groups,
                              mqtt_timeout=1.0,
                              kafka_timeout=0.3)
    bonzo.run()


if __name__ == "__main__":
    main()
