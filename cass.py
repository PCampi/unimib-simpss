import datetime
import json
import os
import time

from tqdm import tqdm

import cassandra
import simpss_persistence


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


if __name__ == "__main__":
    delay = float(os.getenv('DATA_DELAY', '10'))

    addresses = os.getenv('CASSANDRA_CLUSTER_ADDRESSES',
                          'localhost').split(';')

    cluster = cassandra.cluster.Cluster(addresses)
    cc = simpss_persistence.storage.CassandraStorage(cluster)

    keyspace = os.getenv('CASSANDRA_NAMESPACE', 'simpss')
    replication_factor = str(os.getenv('CASSANDRA_REPLICATION', '3'))

    try:
        # setup Cassandra
        cc.connect()
        cc.create_database('simpss', 3)
        cc.set_keyspace('simpss')

        columns = {
            'time_received': 'timestamp',
            'sensor_group': 'text',
            'id': 'int',
            'uptime': 'int',
            'pressure': 'int',
            'temperature': 'int',
            'humidity': 'int',
            'ix': 'int',
            'iy': 'int',
            'iz': 'int',
            'mask': 'int',
        }
        mapping = {
            'id': 'id',
            'time_received': 'time_received',
            'sensor_group': 'sensor_group',
            'uptime': 'uptime',
            'temperature': 'T',
            'pressure': 'P',
            'humidity': 'H',
            'ix': 'Ix',
            'iy': 'Iy',
            'iz': 'Iz',
            'mask': 'M',
        }
        cc.set_name_mapping(mapping)
        cc.set_table('sensor_data', ('row_id', 'text'), columns)

        # setup publisher
        publisher = MockPublisher()
        cc.set_name('sub-1')
        cc.subscribe(publisher)

        datapath = './test_data/log.txt'
        with open(datapath, 'r') as d:
            data = [s for s in tqdm(d.read().split('\n')[:-1])]

        for point in tqdm(data):
            message = json.loads(point)
            publisher.publish(message)
            time.sleep(delay)

    except Exception as e:
        print(e)
    finally:
        cc.disconnect()
