# Istruzioni per l'uso

## Formato dei dati in ingresso a Cassandra

Il database si aspetta dei dati così strutturati:

```javascript
data = {
    "time_received": int,
    "sensor_group": string,
    "sensor_id": int,
    "uptime": int,
    "temperature": int,
    "pressure": int,
    "humidity": int,
    "ix": int,
    "iy": int,
    "iz": int,
    "mask": int,
}
```

I campi `sensor_group`, `sensor_id` e `time_received` formano una chiave primaria composta, `time_received` è il timestamp (int) di ricezione del messaggio dal primo elemento della coda, il *Producer Kafka* che smista i messaggi sui diversi topics.

La conversione tra chiavi nei messaggi avviene nel componente che si occupa di scrivere a database, su Kafka sono presenti soltanto i dati grezzi così come arrivati dal sensore.

# Struttura dei files e dei packages

Il progetto è diviso in tre package Python, `simpss`, `simpss_persistence` e `mocks`.

Il package `simpss` contiene la parte di interfaccia tra EMQ e Kafka, nella classe `MqttKafkaProducer`, il cui utilizzo è dimostrato nel file `stress_producer.py`.

Il package `simpss_persistence` gestisce lo storage su Cassandra e definisce le due interfacce per il pub/sub. L'utilizzo della classe `CassandraStorage` è dimostrato nel file `stress_cassandra.py`.

Il package `mocks` contiene il sensore dummy, utilizzabile per i test di carico.

## Installazione librerie e dipendenze

Per poter essere eseguito il software necessita di:

- Docker
- Python 3.7

Sulle macchine che ospitano il Producer ed il Consumer si consiglia di installare Python ed in seguito creare un virtualenv seguendo questi passi:

```bash
pip install virtualenv
cd /dest/of/virtual/envirnoment
virtualenv .venv # puts the virtual environment in the folder .venv in the local folder
source .venv/bin/activate

pip install -r requirements.txt # install the requirements
```

Il consumer ed il producer sono modificabili direttamente nel codice sorgente o configurabili tramite variabili d'ambiente.

#### Configurazione del Producer

Il producer legge le seguenti variabili d'ambiente per la configurazione del client MQTT

- `MQTT_QOS`: QoS per il broker MQTT (default 2)
- `MQTT_CLIENT_ID`: client id per il client MQTT (default 'prod1')
- `MQTT_ADDRESS`: url del broker MQTT (default 'localhost')
- `MQTT_TOPIC`: nome del topic a cui sottoscrivere (defailt *simpss*)
- `MQTT_MAX_INFLIGHT`: massimo numero di messaggi in volo (default 100)

e le seguenti per la configurazione del Producer Kafka

- `KAFKA_BOOTSTRAP_SERVERS`: urls dei server kafka, completi di porta, opzionalmente divisi da virgola (default "localhost:9092")
- `KAFKA_CLIENT_ID`: id client per Kafka (default "k-prod-1")
- `KAFKA_TIMEOUS_MS`: timeout in millisecondi per la connessione a Kafka (default 6000)
- `KAFKA_MAX_INFLIGHT`: massimo numero di messaggi in volo (default 100)
- `KAFKA_LINGER_MS`: millisecondi di attesa per creare una batch di messaggi (default 1). Se 0, l'invio avviene sequenzialmente un messaggio alla volta (degrada prestazioni).

Inoltre il Producer necessita un mapping nella forma di un dizionario Python al momento della inizializzazione:

```python
sensor_groups = {
    120: 'g1', # id_sensore 120 --> gruppo 'g1'
    121: 'g1', # id_sensore 121 --> gruppo 'g1'
    122: 'g2', # ...
    123: 'g2',
}
```

Questo passo va fatto **manualmente** modificando il codice che crea il Producer, si veda il file `stress_producer.py` per un esempio.

#### Configurazione del Consumer

Il Consumer legge le seguenti variabili d'ambiente per Kafka

- `KAFKA_BOOTSTRAP_SERVERS`: urls dei server di Kafka, completi di porta, opzionalmente separati da virgola (default "localhost:9092")
- `KAFKA_CONSUMER_GROUP_ID`: id del gruppo di consumers a cui il Consumer vuole aggiungersi (default "cg1")

e le seguenti per Cassandra

- `CASSANDRA_CLUSTER_ADDRESSES`: url di un nodo del cluster Cassandra (default localhost)
- `CASSANDRA_KEYSPACE`: nome del keyspace da utilizzare (default "simpss")
- `CASSANDRA_REPLICATION`: replication factor della tabella dati (default 3)

Inoltre la classe `CassandraStorage` necessita di un mapping che identifichi le chiavi delle colonne dati --> colonne tabella, come segue:

```python
mapping = {
    'sensor_group': 'sensor_group',
    'id': 'sensor_id', # 'id' nei dati viene scritto in 'sensor_id' su Cassandra
    'time_received': 'time_received',
    'uptime': 'uptime',
    'T': 'temperature', # 'T' nei dati viene scritto in 'temperature' su Cassandra
    'P': 'pressure',
    'H': 'humidity',
    'Ix': 'ix',
    'Iy': 'iy',
    'Iz': 'iz',
    'M': 'mask',
}
```

Il file `stress_cassandra.py` presenta un esempio di utilizzo.


## Testare Cassandra

Utilizzare questi comandi nella root del progetto:

```bash
docker-compose rm -f
docker-compose pull
docker-compose up --build -d

docker-compose down # alla fine, terminato il test
```

Per effettuare lo stress test, utilizzare i seguenti comandi:

```bash
docker-compose rm -f
docker-compose pull
docker-compose up --build -d

python stress_sensor.py # in un terminale separato
python stress_producer.py # in un terminale separato
python stress_cassandra.py # in un terminale separato

docker-compose down
```

## Eseguire comandi dalla command line di Cassandra

Far partire un Docker container così:

```bash
docker run -it --link nome_container_target:cassandra --rm cassandra:3 cqlsh cassandra
```

che nel nostro caso, visto che il nome del container Cassandra è `cassandra1` e il network creato da compose è `cassandra_simpss-net` sarà:

```bash
docker run -it --network cassandra_simpss-net --link cassandra1:cassandra --rm cassandra:3 cqlsh cassandra
```
