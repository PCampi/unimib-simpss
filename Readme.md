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

La conversione tra chiavi nei messaggi avviene nel componente che si occupa di scrivere a database, su Kafka devono entrare soltanto i dati grezzi così come arrivati dal sensore.

## Testare Cassandra e Graphite/Grafana

Utilizzare questi comandi:

```bash
docker-compose rm -f
docker-compose pull
docker-compose up --build -d
docker-compose down
```

## Eseguire comandi dalla command line di Cassandra

Far partire un Docker container così:

```bash
docker run -it --link nome_container_target:cassandra --rm cassandra:3 cqlsh cassandra
```

che nel mio caso, visto che il nome del container Cassandra è `cassandra1` e il network creato da compose è `cassandra_simpss-net` sarà:

```bash
docker run -it --network cassandra_simpss-net --link cassandra1:cassandra --rm cassandra:3 cqlsh cassandra
```

# Risultati parziali

Ecco un test condotto con

```bash
docker-compose rm -f
docker-compose up --build

python stress_sensor.py
python stress_producer.py
python stress_cassandra.py
```

Il throughput tra Mqtt e Kafka è di 47 messaggi al secondo, il throughput tra Kafka e Cassandra è di 43 messaggi al secondo.
