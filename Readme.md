# Istruzioni per l'uso

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

che nel mio caso, visto che il nome del container Cassandra è `cassandra_graphite` e il network creato da compose è `cassandra_cassandra-network` sarà:

```bash
docker run -it --network cassandra_cassandra-network --link cassandra_graphite:cassandra --rm cassandra:3 cqlsh cassandra
```
