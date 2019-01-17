"""Main file, use it for trying things out."""

import os

from simpss.producers import MqttKafkaProducer

if __name__ == "__main__":
    # MQTT config
    qos = int(os.environ.get("MQTT_QOS", 2))
    client_id = str(os.environ.get("MQTT_CLIENT_ID", 'prod1'))
    mqtt_address = str(os.environ.get("MQTT_ADDRESS", 'localhost'))
    mqtt_topic = str(os.environ.get("MQTT_TOPIC", 'simpss'))
    mqtt_max_inflight = int(os.environ.get("MQTT_MAX_INFLIGHT", 100))
    mqtt_payload_key = str(os.environ.get("MQTT_PAYLOAD_KEY", 'id'))
    mqtt_config = {
        'client-id': client_id,
        'address': mqtt_address,
        'port': 1883,
        'transport': 'tcp',
        'topic': mqtt_topic,
        'qos': qos,
        'max-inflight': mqtt_max_inflight,
        'payload-key': mqtt_payload_key,
    }

    # KAFKA config
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

    sensor_groups = {
        120: 'g1',
        121: 'g1',
        122: 'g2',
        123: 'g2',
    }

    bonzo = MqttKafkaProducer(mqtt_config, kk_config, sensor_groups)
    bonzo.run()
