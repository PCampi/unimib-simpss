"""Main file, use it for trying things out."""

from simpss.producers import MqttKafkaProducer

if __name__ == "__main__":
    # MQTT config
    mqtt_config = {
        'client-id': 'prod1',
        'address': 'localhost',
        'port': 1883,
        'transport': 'tcp',
        'topic': 'simpss',
        'qos': 2,
        'max-inflight': 100,
        'payload-key': 'id',
    }

    # KAFKA config
    kk_config = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 1,
        'session.timeout.ms': 6000,
        # 'enable.idempotence': True,
        'client.id': 'k-prod1',
        'max.in.flight': 100,
        'linger.ms': 1,  # batch together messages every 0.001 seconds
    }

    sensor_groups = {
        120: 'g1',
        121: 'g1',
        122: 'g2',
        123: 'g2',
    }

    bonzo = MqttKafkaProducer(mqtt_config, kk_config, sensor_groups)
    bonzo.run()
