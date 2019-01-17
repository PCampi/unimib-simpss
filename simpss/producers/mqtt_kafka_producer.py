"""File for the MQTT KAFKA producer class."""

import datetime
import json
import logging
import os
import queue
import sys
import time
from typing import Any, Dict, List

import confluent_kafka as ck
import paho.mqtt.client as mq


class MqttKafkaProducer(object):
    """
    MQTT Kafka producer.
    Consumes from an MQTT topic and produces to a Kafka instance.
    """

    def __init__(self, mqtt_config, kafka_config: Dict[str, Any],
                 sensor_groups: Dict[int, str]):
        """
        Create an instance of the Mqtt client and
        the Kafka producer with the specified configuration.

        Needs to know a configuration for the mqtt client, a configuration
        for the Kafka producer, and a mapping between sensor ids and kafka topics.
        It assumes that sensors are part of a group, which is the name of the
        Kafka topic the data will be written to.
        """
        self.messages_read_from_mqtt = 0
        self.messages_sent_to_kafka = 0

        producer_name = "{}-{}".format(
            str(kafka_config['group.id']), str(kafka_config['client.id']))
        self.__logger = self.__get_logger(producer_name)

        self.__logger.info("Setting up mqtt and kafka")
        self.__setup_mqtt(mqtt_config)
        self.__setup_kafka(kafka_config)
        self.__sensor_map = sensor_groups
        self.queue: queue.Queue = queue.Queue(maxsize=5000)
        self.__logger.info("Finished configuration for mqtt and Kafka")

    def __setup_mqtt(self, mqtt_config):
        mq_required_keys = set([
            'client-id', 'address', 'port', 'transport', 'topic', 'qos',
            'max-inflight', 'payload-key'
        ])
        if not all(k in mqtt_config.keys() for k in mq_required_keys):
            raise ValueError(
                "Required keys for Mqtt configuration are missing!")

        self._mqtt_address = str(mqtt_config['address'])
        self._mqtt_port = int(mqtt_config['port'])
        self._mqtt_topic = str(mqtt_config['topic'])
        self._mqtt_payload_key = mqtt_config['payload-key']

        mqtt_client_id = str(mqtt_config['client-id'])
        mqtt_transport = str(mqtt_config['transport'])
        mqtt_qos = int(mqtt_config['qos'])
        mqtt_max_inflight = int(mqtt_config['max-inflight'])

        self._mq_client = mq.Client(
            client_id=mqtt_client_id,
            clean_session=True,
            transport=mqtt_transport)
        self._mq_client.max_inflight_messages_set(mqtt_max_inflight)
        self._mq_client.on_connect = self._on_mqtt_connect(
            self._mqtt_topic, mqtt_qos)
        self._mq_client.on_log = self._on_log
        self._mq_client.on_message = self._on_mqtt_message
        self._mq_client.on_disconnect = self._on_mqtt_disconnect

        self.__logger.info("Created mqtt client with id: " + mqtt_client_id)

    def __setup_kafka(self, kafka_config):
        if 'bootstrap.servers' not in kafka_config.keys():
            raise ValueError("Missing bootstrap.servers key in kafka config")

        self.__logger.info("Creating Kafka producer with configuration {}".
                           format(kafka_config))
        self._kf_producer: ck.Producer = ck.Producer(
            kafka_config, logger=self.__logger)
        self.__logger.info("Created Kafka producer")

    def run(self):
        """
        Run the clients.
        """
        self._mq_client.connect(
            self._mqtt_address, port=self._mqtt_port, keepalive=60)

        try:
            while True:
                # poll the mqtt client for network events
                # things will happen in the on_message callback
                self._mq_client.loop(timeout=1.0)

                # the queue should contain messages at this point
                try:  # get all messages from the queue and send them to Kafka
                    while True:
                        # raises if empty, so don't worry of infinite loops
                        message_dict = self.queue.get_nowait()
                        kafka_topic = str(message_dict['sensor_group'])
                        message_str = json.dumps(
                            message_dict, ensure_ascii=False)
                        message = message_str.encode('utf-8')

                        # produce to kafka and poll for 0.3 seconds max
                        self._kf_producer.produce(
                            kafka_topic,
                            message,
                            callback=self.__delivery_report)
                        self._kf_producer.poll(0.3)

                except queue.Empty:
                    continue

        except KeyboardInterrupt:
            self.__logger.info("Stopping mqtt and Kafka clients")
            self._mq_client.unsubscribe(self._mqtt_topic)
            self.__logger.info(
                "Awaiting 5 seconds to flush the Kafka producer")
            self._kf_producer.flush(5)
            self.__logger.info("Kafka client flushed")
        finally:
            self._mq_client.loop_start()
            time.sleep(2)
            self._mq_client.loop_stop()

    def _on_mqtt_connect(self, topic, qos):
        def on_connect(client: mq.Client, userdata, flags, rc):
            """
            Callback called on connection event.
            """
            if rc == 0:
                self.__logger.info("Connected to " + client._host)
                # subscribe to a topic - once subscribed, the callback
                # will trigger the client loop
                self.__logger.info("Subscribing to topic " + topic +
                                   " with qos=" + str(qos))
                client.subscribe(topic, qos=qos)
            elif rc == 1:
                self.__logger.error(
                    "Connection refused - incorrect protocol version")
            elif rc == 2:
                self.__logger.error(
                    "Connection refused - invalid client identifier")
            elif rc == 3:
                self.__logger.error("Connection refused - server unavailable")
            elif rc == 4:
                self.__logger.error(
                    "Connection refused - bad username or password")
            elif rc == 5:
                self.__logger.error(" Connection refused - not authorised")

        return on_connect

    def _on_mqtt_disconnect(self, client: mq.Client, userdata, rc):
        """
        Disconnection callback.
        """
        if rc == 0:
            self.__logger.info("Peacefully disconnected.")
        else:
            self.__logger.warning("Unexpected disconnection")

    def _on_mqtt_subscribe(self, client: mq.Client, userdata, mid,
                           granted_qos: List[int]):
        """
        Called when a subscription answer is received from the broker.
        """
        self.__logger.info("Subscribed")

    def _on_mqtt_unsubscribe(self, client, userdata, mid):
        self.__logger.info("Unsubscribed")
        self._mq_client.disconnect()

    def _on_mqtt_message(self, client: mq.Client, userdata,
                         message: mq.MQTTMessage):
        """
        Called on message received.
        Forwards message to the appropriate Kafka topic.
        """
        payload_bytes = message.payload
        payload_str = payload_bytes.decode("utf-8")
        payload = json.loads(payload_str)

        payload['time_received'] = datetime.datetime.now().isoformat()
        payload['sensor_group'] = self.__sensor_map[payload[self.
                                                            _mqtt_payload_key]]

        self.queue.put(payload)

    def _on_log(self, client: mq.Client, userdata, level, buf):
        """
        Called on logging by Mqtt client.
        """
        self.__logger.debug(str(buf))

    def __delivery_report(self, err, msg):
        """
        Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush().
        """
        if err is not None:
            # TODO: fix this to error
            self.__logger.warning('Message delivery failed: {}'.format(err))
        else:
            self.__logger.info('Message delivered to {} [{}]'.format(
                msg.topic(), msg.partition()))

    def __get_logger(self, name='py-producer'):
        """
        Creates a logger for this class.
        """
        logger = logging.getLogger(name=name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        return logger
