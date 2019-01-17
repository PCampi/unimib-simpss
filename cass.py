import datetime
import json
import os
import time

from tqdm import tqdm

import cassandra
import simpss_persistence

LOGGER = simpss_persistence.custom_logging.get_logger('main')


class MockPublisher(simpss_persistence.pub_sub.Publisher):
    def __init__(self):
        self.subscribers = dict()

    def add_subscriber(self, sub_obj, sub_name):
        if sub_name not in self.subscribers:
            self.subscribers[sub_name] = sub_obj
        else:
            raise ValueError(
                "Subscriber with name {} already exists".format(sub_name))

    def remove_subscriber(self, name):
        subscriber = self.subscribers.pop(name, None)
        if subscriber is None:
            print("Trying to remove subscriber {} which does not exist!".
                  format(name))

    def publish(self, message):
        message['time_received'] = datetime.datetime.now()
        message['sensor_group'] = 'g1'

        for _, subscriber in self.subscribers.items():
            subscriber.receive(message)


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


if __name__ == "__main__":
    delay = float(os.getenv('DATA_DELAY', '10'))

    addresses = os.getenv('CASSANDRA_CLUSTER_ADDRESSES',
                          'localhost').split(';')
    keyspace = os.getenv('CASSANDRA_NAMESPACE', 'simpss')
    replication_factor = str(os.getenv('CASSANDRA_REPLICATION', '3'))

    cluster = cassandra.cluster.Cluster(addresses)
    session = cluster.connect()
    create_database(keyspace, replication_factor, session)
    create_table(keyspace, 'sensor_data', session)
    session.shutdown()

    cc_cluster = cassandra.cluster.Cluster(addresses)
    cc = simpss_persistence.storage.CassandraStorage(cc_cluster)

    try:
        # setup Cassandra
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

        # setup publisher
        publisher = MockPublisher()
        cc.set_subscriber_name('sub-1')
        cc.subscribe(publisher)

        datapath = './test_data/log.txt'
        with open(datapath, 'r') as d:
            data = [s for s in tqdm(d.read().split('\n')[:-1])]
        
        messages = [json.loads(p) for p in tqdm(data)]

        if delay > 0.0:
            for message in tqdm(messages):
                publisher.publish(message)
                time.sleep(delay)
        else:
            for message in tqdm(messages):
                publisher.publish(message)


    except Exception as e:
        print(e)
    finally:
        cc.disconnect()
