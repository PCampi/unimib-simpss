"""Main di prova per Apache Cassandra."""

# idealmente dovrebbe fare questo:
# 1. alla connessione controllare quali keyspace ci sono.
#   1a: se il keyspace 'simpss' esiste, continua al punto 2
#   1b: se 'simpss' non esiste, crealo con una query
# 2. connettiti a Kafka come consumer
#   - quale consumer group?
#   - a quali topic sottoscrivi?
# 3. ascolta i topic Kafka. Quando arriva un messaggio:
#   a. prendi id sensore e timestamp di ricezione del messaggio
#   b. concatenali per usarli come RowKey in Cassandra
#   c. esegui una insert in Cassandra

import logging
import os
from typing import List

from cassandra import cluster as cc


def get_logger(name='main'):
    """Get default logger."""
    logger = logging.getLogger(name='Main logger')
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


def create_keyspace_if_not_exists(ks_name: str, replication_factor: int,
                                  session: cc.Session, logger: logging.Logger):
    """
    Create a keyspace if it does not exist in Cassandra.
    A keyspace is like a SQL Database.
    """
    existing_ks = session.execute(
        "SELECT keyspace_name FROM system_schema.keyspaces")
    if existing_ks.one():  # there is at leas one keyspace
        # but it is not the correct one we are looking for --> create it
        if ks_name not in [eks.keyspace_name for eks in existing_ks]:
            logger.info("Creating keyspace %s", ks_name)
            query_string = "CREATE KEYSPACE %(ks)s with replication = {'class': 'SimpleStrategy', 'replication_factor': %(rf)s}" % {
                'ks': ks_name,
                'rf': replication_factor
            }
            session.execute(query_string, timeout=5.0)
        else:  # already exists
            logger.info("Keyspace %s already exists, skipping creation",
                        ks_name)
    else:  # does not exist
        logger.info("Creating keyspace %s", ks_name)
        session.execute(
            """
        CREATE KEYSPACE %s
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '%(rep_fac)s'}
        """, (ks_name, replication_factor),
            timeout=5.0)


def create_column_family_if_not_exist(column_family: str, session: cc.Session):
    """
    Create a column family (aka SQL table) if it does not exist.
    """
    query_string = """
    CREATE TABLE IF NOT EXISTS %s
    (
        row_id text PRIMARY KEY,
        sensor_id int,
        uptime int,
        pressure int,
        temperature int,
        humidity int,
        ix int,
        iy int,
        iz int,
        mask int
    )
    """ % column_family
    session.execute(query_string)


if __name__ == "__main__":
    logger = get_logger('main')

    addresses: List[str] = os.getenv('CASSANDRA_CLUSTER_ADDRESSES',
                                     'localhost').split(';')
    logger.info("Cassandra cluster address: {}".format(";".join(addresses)))

    keyspace = os.getenv('CASSANDRA_NAMESPACE', 'simpss')
    replication_factor = str(os.getenv('CASSANDRA_REPLICATION', '3'))
    logger.info("Cassandra keyspace is {} with replication {}".format(
        keyspace, replication_factor))

    cassandra_cluster = cc.Cluster(addresses)
    logger.info("Connecting to cluster")
    session = cassandra_cluster.connect()
    logger.info("Connected to cluster")

    try:
        create_keyspace_if_not_exists(keyspace, 3, session, logger)

        logger.info("Setting keyspace")
        session.set_keyspace(keyspace)
        logger.info("Keyspace set")

        logger.info("Creating table 'sensor_data' if not exists")
        create_column_family_if_not_exist('sensor_data', session)
        logger.info("Done")
    except Exception as e:
        print(e)
    finally:
        session.shutdown()
