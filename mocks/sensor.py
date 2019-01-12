"""Fake sensor."""

import datetime
import json
import logging
import os
import sys
import time
from typing import List
import numpy as np
from tqdm import tqdm

import paho.mqtt.client as mq

NAME = "Sensor"
logger = logging.getLogger(name=NAME)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def on_log(client, userdata, level, buf):
    """
    Logging callback.
    """
    logger.info(str(buf))


def on_connect(client: mq.Client, userdata, flags, rc):
    """
    Callback called on connection event.
    """
    if rc == 0:
        logger.info("Connected to " + client._host)
    elif rc == 1:
        logger.error("Connection refused - incorrect protocol version")
    elif rc == 2:
        logger.error("Connection refused - invalid client identifier")
    elif rc == 3:
        logger.error("Connection refused - server unavailable")
    elif rc == 4:
        logger.error("Connection refused - bad username or password")
    elif rc == 5:
        logger.error(" Connection refused - not authorised")


def on_disconnect(client: mq.Client, userdata, rc):
    """
    Disconnection callback.
    """
    if rc == 0:
        logger.info("Peacefully disconnected.")
    else:
        logger.warning("Unexpected disconnection")

    client.loop_stop()
    logger.info("Stopped client loop")


def on_subscribe(client: mq.Client, userdata, mid, granted_qos: List[int]):
    """
    Called on subscription successful.
    """
    # log and start the client loop
    logger.info("Subscribed")
    # client.loop_start()


def on_message(client: mq.Client, userdata, message: mq.MQTTMessage):
    """
    Callback called when a message is received.
    """
    payload_bytes = message.payload
    payload_str = payload_bytes.decode("utf-8")

    logger.info("Received message " + payload_str)


def on_publish(client, userdata, mid):
    """
    Called whenever a message is successfully published.
    """
    logger.debug("Published message with id " + str(mid))


def run_sensor(datapath: str, topic: str, publish_every=0.25):
    """
    Main function of this module.

    Parameters
    ----------
    datapath: str
        absolute path to real sensor data
    
    topic: str
        mqtt topic on which to publish data
    
    publis_every: float
        time delay between two data points are published. It is
        awaited with time.sleep(publish_every)
    """
    logger.info("Reading data file {}".format(datapath))
    with open(datapath, 'r') as d:
        data = [s.encode() for s in tqdm(d.read().split('\n')[:-1])]

    mqtt_address = 'localhost'
    mqtt_port = 1883
    mqtt_transport = 'tcp'
    mqtt_topic = 'simpss'
    mqtt_qos = 2
    mqtt_max_inflight = 50

    # create the client and set it up
    logger.info("Creating client " + NAME)
    client = mq.Client(
        client_id=NAME, clean_session=True, transport=mqtt_transport)
    client.max_inflight_messages_set(mqtt_max_inflight)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_log = on_log
    client.on_publish = on_publish
    logger.info("Client " + NAME + " created")

    # connect to the MQTT broker - all action happens in the callbacks
    logger.info("Connecting to " + mqtt_address)
    client.connect(mqtt_address, port=mqtt_port, keepalive=60)

    # start publishing messages
    try:
        i = 0
        for point in data:
            client.publish(
                mqtt_topic, payload=point, qos=mqtt_qos, retain=False)
            i += 1
            if i == 5:
                result = client.loop(timeout=1.0)
                i = 0
                if result != 0:
                    logger.error("Mqtt client returned code {}".format(result))
            time.sleep(publish_every)
    except KeyboardInterrupt:
        client.disconnect()
        time.sleep(3)
