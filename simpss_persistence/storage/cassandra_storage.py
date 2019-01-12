"""Storage class for Cassandra backend."""

import datetime
import logging
import time
import warnings
from typing import Any, Dict, List, Tuple

from cassandra import cluster as cc

from ..custom_logging import get_logger
from ..data_mapping import convert
from ..pub_sub import Publisher, Subscriber
from .base_storage import BaseStorage


class CassandraStorage(BaseStorage, Subscriber):
    """
    Cassandra storage implementation.

    Subscribes to a Kafka consumer and sends the message
    it receives to the Cassandra cluster.

    Steps to use this class are:
    1. create with a cluster
    2. connect to the cluster
    3. set keyspace and table calling set_keyspace_table
    4. set mapping from data columns to table columns
    5. set_name: name for the subscriber
    6. subscribe to a publisher
    7. enjoy!

    WARNING: it only works for compound primary keys in Cassandra!!!
    """

    def __init__(self, cluster: cc.Cluster):
        self.cluster = cluster
        self.__logger = get_logger(name='CassandraStorage')

    def connect(self):
        """Connect to storage backend."""
        self.__logger.info("Connecting cluster")
        self.session = self.cluster.connect()
        self.__logger.info("Connected")

    def disconnect(self):
        """Disconnect gracefully."""
        self.__logger.info("Disconnecting from cluster")
        self.session.shutdown()
        self.__logger.info("Disconnected. Goodbye.")

    def set_keyspace_table(self, keyspace, table):
        """
        Set the keyspace and table names.
        """
        self.__keyspace = keyspace
        self.__table = table

    def set_name_mapping(self, data_to_db_mapping: Dict[str, str]):
        """
        Sets mapping between data columns and table columns.
        Must be called before any row_insert.

        Parameters
        ----------
        data_to_db_mapping: Dict[str: str]
            mapping between the input data column names and the Cassandra table column names,
            e.g. {'T': 'temperature'} will consider data column 'T' to correspond
            to Cassandra column 'temperature'
        """
        self.mapping = data_to_db_mapping
        self.__columns = [v for _, v in data_to_db_mapping.items()]
        self.__prepare_statement(self.__columns)

    def insert_row(self, row: Dict[str, Any]):
        """
        Insert a row into Cassandra. The row should have the right column names
        already defined, else an error from the database will be raised.
        """
        converted_row = convert(row, self.mapping)
        values = tuple(
            converted_row.get(column, None) for column in self.__columns)

        self.session.execute(self.__statement, values)

    def __prepare_statement(self, columns):
        """
        Prepare the insert statement to be executed everytime for each row.
        """
        query = "INSERT INTO %s.%s (" % (self.__keyspace, self.__table)

        for column in columns:
            query += "%s, " % column

        query = query[:-2]  # delete last ', '
        query += ") VALUES ("

        for _ in columns:
            query += "?, "

        query = query[:-2]  # delete last ', '
        query += ")"

        self.__logger.debug("Prepared statement is {}".format(query))
        self.__statement = self.session.prepare(query)
        self.__logger.info("Statement prepared successfully")

    def set_subscriber_name(self, name):
        self.sub_name = name

    def subscribe(self, publisher: Publisher):
        if not self.__columns:
            raise AttributeError(
                "Must initialize the mapping before subscribing. Call set_name_mapping."
            )
        publisher.add_subscriber(self, self.sub_name)

    def receive(self, message):
        """
        Receive a message from the publisher to insert into Cassandra.
        """
        if not isinstance(message, dict):
            raise ValueError("Message should be a dict, got {} instead".format(
                str(type(message))))
        self.insert_row(message)
