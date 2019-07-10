"""File linking the Kafka cluster to Cassandra."""

import datetime
import json
import os
import time

from tqdm import tqdm

import cassandra
import simpss_persistence
import utils

LOGGER = simpss_persistence.custom_logging.get_logger('main')


def create_database(db_name, replication_factor,
                    session: cassandra.cluster.Session):
    query = """
    CREATE KEYSPACE IF NOT EXISTS %s
    WITH REPLICATION = {
        'class': 'SimpleStrategy',
        'replication_factor': %s
    }
    """ % (db_name, replication_factor)
    LOGGER.debug("Executing query {}".format(query))
    session.execute(query)
    LOGGER.debug("query executed")


def create_table(keyspace, name, session):
    query = """
    CREATE TABLE IF NOT EXISTS %s.%s (
        time_received timestamp,
        sensor_group text,
        sensor_id int,
        uptime int,
        temperature int,
        pressure int,
        humidity int,
        ix int,
        iy int,
        iz int,
        mask int,
        PRIMARY KEY (sensor_group, sensor_id, time_received)
    )
    """ % (keyspace, name)
    LOGGER.debug("Create table: executing query {}".format(query))
    session.execute(query)
    LOGGER.debug("query executed")


def main():
    LOGGER.info("reading sensor file")
    sensor_groups = utils.read_sensor_group_mapping(
        os.path.join(os.getcwd(), 'sensor_group.csv'))
    LOGGER.info(f"configuration read: {str(sensor_groups)}")
    unique_groups = set([x for _, x in sensor_groups.items()])
    consumer_groups = [g for g in unique_groups]

    addresses = os.getenv('CASSANDRA_CLUSTER_ADDRESSES',
                          'localhost').split(';')
    keyspace = os.getenv('CASSANDRA_KEYSPACE', 'simpss')
    replication_factor = str(os.getenv('CASSANDRA_REPLICATION', '3'))

    LOGGER.info(f"cassandra addresses: {addresses}")
    LOGGER.info(f"cassandra keyspace: {keyspace}")
    LOGGER.info(f"cassandra replication factor: {replication_factor}")

    cluster = cassandra.cluster.Cluster(addresses)
    session = cluster.connect()
    create_database(keyspace, replication_factor, session)
    create_table(keyspace, 'sensor_data', session)
    session.shutdown()

    cc_cluster = cassandra.cluster.Cluster(addresses)
    cc = simpss_persistence.storage.CassandraStorage(cc_cluster)

    # KAFKA
    bootstrap_servers = str(
        os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'))
    consumer_group_id = str(os.environ.get('KAFKA_CONSUMER_GROUP_ID', 'cg1'))

    LOGGER.info(f"kafka bootstrap servers: {bootstrap_servers}")
    LOGGER.info(f"kafka consumer group id: {consumer_group_id}")

    try:
        # setup Cassandra
        LOGGER.info("connecting to cassandra")
        cc.connect()
        cc.set_keyspace_table(keyspace, 'sensor_data')

        mapping = {
            'sensor_group': 'sensor_group',
            'id': 'sensor_id',
            'time_received': 'time_received',
            'uptime': 'uptime',
            'T': 'temperature',
            'P': 'pressure',
            'H': 'humidity',
            'Ix': 'ix',
            'Iy': 'iy',
            'Iz': 'iz',
            'M': 'mask',
        }
        cc.set_name_mapping(mapping)

        # setup kafka consumer and subscribe to Kafka
        LOGGER.info("creating kafka consumer")
        kafka_consumer = simpss_persistence.kafka_consumer.KafkaConsumer(
            bootstrap_servers, consumer_group_id)

        LOGGER.info(f"subscribing consumer to groups: {consumer_groups}")
        kafka_consumer.kafka_subscribe(consumer_groups)

        # add Cassandra storage as a subscriber to the consumer and run it
        cc.set_subscriber_name('sub-1')
        cc.subscribe(kafka_consumer)

        # start
        kafka_consumer.start_consuming()
    except Exception as e:
        print(e)
    finally:
        cc.disconnect()


if __name__ == "__main__":
    main()
