"""Kafka consumer."""
import json
from typing import Any, Dict, List, Union

from confluent_kafka import Consumer, Message
from ..custom_logging import get_logger
from ..pub_sub import Publisher, Subscriber


class KafkaConsumer(Publisher):
    """
    Consumer for Kafka, which publishes to all subscribed clients.
    """

    def __init__(self, bootstrap_servers: str, group_id: str):
        """
        Kafka consumer class which implements also the Publisher interface.
        Messages consumed from Kafka should be strings representing valid
        JSON objects.

        Parameters
        ----------
        bootstrap_servers: list of str
            addresses of the Kafka servers

        group_id: str
            consumer group id
        """
        self.__logger = get_logger('consumer-{}'.format(group_id))
        self.subscribers: Dict[str, Subscriber] = dict()
        self.running = False

        config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'enable.auto.commit': True,
        }
        self.kafka = Consumer(config)

    def kafka_subscribe(self, topic: Union[str, List[str]]):
        if isinstance(topic, list):
            self.kafka.subscribe(topic)
        elif isinstance(topic, str):
            self.kafka.subscribe([topic])

    def start_consuming(self):
        """
        Start consuming messages from Kafka.
        Every consumed message is then passed to all subscribers.
        """
        try:
            self.running = True
            while self.running:
                messages = self.kafka.consume(10, timeout=1.0)

                if messages:  # consumed some messages from Kafka
                    valid_messages = []
                    # check every message, if ok send to Subscriber, else log error
                    for message in messages:
                        if message.error():  # error receiving this message
                            pass
                            # self.__logger.error("Kafka error {}".format(
                            #     message.error().str()))
                        else:
                            valid_messages.append(message)

                    # self.__logger.info("Valid messages/total: {}/{}".format(
                    #     len(valid_messages), len(messages)))
                    for message in valid_messages:
                        self.publish(message)
        except (KeyboardInterrupt, SystemExit):
            self.on_shutdown()

    def add_subscriber(self, sub_obj, sub_name):
        """
        Add subscriber.

        Parameters
        ----------
        sub_obj: Subscriber
            the subscriber object

        sub_name: str
            name of the subscriber. If already present, raises ValueError
        """
        if sub_name not in self.subscribers:
            self.subscribers[sub_name] = sub_obj
        else:
            raise ValueError(
                "Subscriber with name {} already exists".format(sub_name))

    def remove_subscriber(self, name):
        """
        Remove a subscriber by the name `name`.

        Parameters
        ----------
        name: str
            name of the subscriber to delete
        """
        # removes the subscriber and returns it, or None
        subscriber = self.subscribers.pop(name, None)
        if subscriber is None:
            self.__logger.error(
                "Trying to remove subscriber with name {}, which does not exist."
                .format(name))

    def publish(self, message: Any):
        """
        Send a message to all subscribers.

        Parameters
        ----------
        message: Any
            the message to send
        """
        # pylint: disable=E1120
        decoded = self.__decode(message)
        if decoded:  # if it's not None :)
            for _, subscriber in self.subscribers.items():
                subscriber.receive(decoded)

    def __decode(self, message: Message):
        """
        Decode a message coming from Kafka.
        It will become a Python Dict
        """
        value = message.value()  # can be None, str, bytes

        if value:
            value = json.loads(value, encoding='utf-8')

        return value

    def on_shutdown(self):
        self.running = False
        self.subscribers = None
        self.kafka.close()
