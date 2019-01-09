import os
import simpss_persistence

if __name__ == "__main__":
    addresses = os.getenv('CASSANDRA_CLUSTER_ADDRESSES',
                          'localhost').split(';')
    cc = simpss_persistence.storage.CassandraStorage(addresses)

    keyspace = os.getenv('CASSANDRA_NAMESPACE', 'simpss')
    replication_factor = str(os.getenv('CASSANDRA_REPLICATION', '3'))

    try:
        cc.connect()
        cc.create_database('simpss', 3)
        cc.set_keyspace('simpss')

        columns = {
            'sensor_id': 'int',
            'uptime': 'int',
            'pressure': 'int',
            'temperature': 'int',
            'humidity': 'int',
            'ix': 'int',
            'iy': 'int',
            'iz': 'int',
            'mask': 'int',
        }
        cc.create_table('sensor_data', ('row_id', 'text'), columns)
    except Exception as e:
        print(e)
    finally:
        cc.disconnect()
