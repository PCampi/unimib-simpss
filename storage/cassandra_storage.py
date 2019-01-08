"""Storage class for Cassandra backend."""

import logging
from typing import Any, Dict, List, Tuple
import warnings

from cassandra import cluster as cc

from .base_storage import BaseStorage


def get_logger(name: str):
    """Get a logger to use in this class."""
    logger = logging.getLogger(name=name)
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


class CassandraStorage(BaseStorage):
    """
    Cassandra storage implementation.
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
        self.session.shutdown()

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

        # pylint: disable=E1120
        self._prepare_statement()

    def insert_row(self, row: Dict[str, Any]):
        # TODO: ugly temporary warning workaround
        warnings.warn(
            "Blocking call to session.execute may degrade performance",
            category=ResourceWarning)

        # get the values from the row, using the expected column names
        values_to_insert = tuple(
            row.get(column_name, None) for column_name in self.__columns)
        self.session.execute(self.__statement, values_to_insert)

    def receive(self, row: Dict[str, Any]):
        """
        Receive a message to insert into Cassandra.
        Used for the Observer pattern with the Kafka producer.
        """
        # pylint: disable=E1120
        self.insert_row(row)

    def _prepare_statement(self):
        query = "INSERT INTO %s.%s (%s, " % (self.__keyspace, self.__table,
                                             self.__pk)

        column_names = [c for c in self.__columns.keys()]

        for column in column_names:
            query += "%s, " % column

        query = query[:-2]  # delete last ', '
        query += ") VALUES ("

        for _ in range(len(column_names)):
            query += "?, "

        query = query[:-2]  # delete last ', '
        query += ")"

        self.__logger.debug("Prepared statement is {}".format(query))
        self.__statement = self.session.prepare(query)
        self.__logger.info("Statement prepared successfully")
