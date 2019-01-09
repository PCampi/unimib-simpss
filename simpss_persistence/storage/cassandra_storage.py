"""Storage class for Cassandra backend."""

import logging
import warnings
from typing import Any, Dict, List, Tuple

from cassandra import cluster as cc

from ..custom_logging import get_logger
from ..pub_sub import Publisher, Subscriber
from .base_storage import BaseStorage


class CassandraStorage(BaseStorage, Subscriber):
    """
    Cassandra storage implementation.

    Subscribes to a Kafka consumer and sends the message
    it receives to the Cassandra cluster.
    """

    def __init__(self, storage_addresses: List[str]):
        self.storage_addresses = storage_addresses
        self.cluster: cc.Cluster = cc.Cluster(storage_addresses)
        self.__logger = get_logger(name='CassandraStorage')

    def connect(self):
        """Connect to storage backend."""
        self.session = self.cluster.connect()

    def disconnect(self):
        """Disconnect gracefully."""
        self.__logger.info("Disconnecting from cluster")
        self.session.shutdown()
        self.__logger.info("Disconnected. Goodbye.")

    def create_database(self, db_name: str, replication: int):
        """
        Create a keyspace if it does not exist in Cassandra.
        A keyspace is like a SQL Database.
        """
        self.__keyspace = db_name

        existing_ks = self.session.execute(
            "SELECT keyspace_name FROM system_schema.keyspaces")
        if existing_ks.one():  # there is at leas one keyspace
            # but it is not the correct one we are looking for --> create it
            if db_name not in [eks.keyspace_name for eks in existing_ks]:
                self.__logger.info("Creating keyspace %s", db_name)
                query_string = "CREATE KEYSPACE %(ks)s with replication = {'class': 'SimpleStrategy', 'replication_factor': %(rf)s}" % {
                    'ks': db_name,
                    'rf': replication
                }
                self.session.execute(query_string, timeout=5.0)
            else:  # already exists
                self.__logger.info(
                    "Keyspace %s already exists, skipping creation", db_name)
        else:  # does not exist
            self.__logger.info("Creating keyspace %s", db_name)
            self.session.execute(
                """
            CREATE KEYSPACE %s
            WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '%(rep_fac)s'}
            """, (db_name, replication),
                timeout=5.0)

    def create_table(self, table_name: str, primary_key: Tuple[str, str],
                     columns: Dict[str, str]):
        """
        Create a column family (aka SQL table) if it does not exist.
        """
        pk_name, pk_type = primary_key
        self.__pk = pk_name
        self.__table = table_name
        self.__columns = columns

        query_string = "CREATE TABLE IF NOT EXISTS " + table_name
        query_string += " ( %s %s " % (pk_name, pk_type) + " PRIMARY KEY,\n"

        for col_name, col_type in columns.items():
            query_string += "{} {}".format(col_name, col_type)
            query_string += ",\n"

        query_string = query_string[:-2]  # delete the last \n and comma
        query_string += ")"
        self.__logger.debug("Executing query: {}".format(query_string))

        self.__logger.info("Creating column family (=table)")
        self.session.execute(query_string)
        self.__logger.info("Column family created")

        self._prepare_statement()

    def set_keyspace(self, keyspace: str):
        self.session.set_keyspace(keyspace)

    def insert_row(self, row: Dict[str, Any]):
        # TODO: ugly temporary warning workaround
        warnings.warn(
            "Blocking call to session.execute may degrade performance",
            category=ResourceWarning)

        # get the values from the row, using the expected column names
        # use None if have missing data
        values_to_insert = tuple(
            row.get(column_name, None) for column_name in self.__columns)

        self.__logger.info("Sending data to Cassandra")
        self.session.execute(self.__statement, values_to_insert)
        self.__logger.info("Data sent")

    def _prepare_statement(self):
        query = "INSERT INTO %s.%s (%s, " % (self.__keyspace, self.__table,
                                             self.__pk)

        column_names = [c for c in self.__columns.keys()]

        for column in column_names:
            query += "%s, " % column

        query = query[:-2]  # delete last ', '
        query += ") VALUES ("

        for _ in range(len(column_names) + 1):  # add 1 for the primary key
            query += "?, "

        query = query[:-2]  # delete last ', '
        query += ")"

        self.__logger.debug("Prepared statement is {}".format(query))
        self.__statement = self.session.prepare(query)
        self.__logger.info("Statement prepared successfully")

    def set_name(self, name):
        self.sub_name = name

    def subscribe(self, publisher: Publisher):
        publisher.add_subscriber(self, self.sub_name)

    def receive(self, message):
        """
        Receive a message from the publisher to insert into Cassandra.
        """
        if not isinstance(message, dict):
            raise ValueError("Message should be a dict, got {} instead".format(
                str(type(message))))
        self.insert_row(message)
