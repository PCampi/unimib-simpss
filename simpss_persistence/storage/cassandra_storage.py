"""Storage class for Cassandra backend."""

import datetime
import logging
import time
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

    Steps to use this class are:
    1. create with a cluster
    2. connect to the cluster
    3. create_database
    4. create_table
    5. set_keyspace
    6. set mapping from data columns to table columns
    7. set_name: name for the subscriber
    8. subscribe to a publisher
    9. enjoy!
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

    def set_name_mapping(self, mapping: Dict[str, str]):
        """
        Sets mapping between data columns and table columns.
        Must be called before any row_insert.

        Parameters
        ----------
        mapping: Dict[str: str]
            mapping between the table column names and the data column names,
            e.g. {'temperature': 'T'} will consider data column 'T' to correspond
            to Cassandra column 'temperature'
        """
        self.mapping = mapping

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

    def set_table(self, table_name: str, primary_key: Tuple[str, str],
                  columns: Dict[str, str]):
        """
        Create a table if it does not exist. Set the columns of the table
        to the value of `columns` and creates an internal mapping between
        the data columns and the table columns using `mapping`

        Parameters
        ----------
        table_name: str 
            name of the table to create

        primary_key: Tuple[str: str]
            primary key in tuple format, should be ('pk_name', 'pk_type')
        
        columns: Dict[str: str]
            columns of the table
        """
        if not self.mapping:
            err = """Mapping from table to data column names is not set!
            You should first call set_name_mapping before using this class to
            persist data to Cassandra."""
            raise AttributeError(err)

        pk_name, pk_type = primary_key
        self.__pk = pk_name
        self.__table = table_name
        self.__columns: Dict[str, str] = columns

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
        time_received = row.get('time_received', time.time())
        if hasattr(time_received, 'timestamp'):
            time_received = time_received.timestamp()
        sensor_group = row.get('sensor_group', '1')

        row[self.__pk] = str(sensor_group) + '-' + str(time_received)

        # get right columns for query
        # we know the table columns, must map them to the data columns
        data_columns = [self.__pk]
        for c in self.__columns.keys():
            data_columns.append(self.mapping[c])

        # get the values from the row, using the expected column names
        # use None if have missing data
        values_to_insert = tuple(
            row.get(column_name, None) for column_name in data_columns)

        self.session.execute(self.__statement, values_to_insert)

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
