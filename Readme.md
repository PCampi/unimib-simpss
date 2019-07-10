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
docker run -it --link nome_container_target:cassandra --rm cassandra:3.11 cqlsh cassandra
```

che nel nostro caso, visto che il nome del container Cassandra è `cassandra1` e il network creato da compose è `cassandra_simpss-net` sarà:

```bash
docker run -it --network unimibsimpss_simpss-net --link cassandra1:cassandra --rm cassandra:3.11 cqlsh cassandra
```

# Deploy sulle macchine MGH

## Creazione dei dischi e delle partizioni

I dischi vanno formattati in `ext4` per essere utilizzati. Vogliamo usate `dev/sda` per kafka/zookeeper e montarlo su `/mnt/kafka-zookeeper`, mentre useremo `/dev/sdb` montato su `/mnt/cassandra` per cassandra.

Prima di tutto, formattare i dischi:
```bash
# primo disco, generalmente su /dev/sda
sudo parted /dev/sda mklabel gpt
# creo la partizione
sudo parted -a opt /dev/sda mkpart primary ext4 0% 100%
# formatto la partizione in ext4
sudo mkfs.ext4 -L kafka-zookeeper /dev/sda1

# secondo disco, generalmente su /dev/sdb
sudo parted /dev/sdb mklabel gpt
# creo la partizione
sudo parted -a opt /dev/sdb mkpart primary ext4 0% 100%
# formatto la partizione in ext4
sudo mkfs.ext4 -L cassandra /dev/sdb1
```

Poi modificare il file `/etc/fstab` aggiungendo le seguenti righe:

```txt
LABEL=kafka-zookeeper /mnt/kafka-zookeeper ext4 defaults 0 2
LABEL=cassandra /mnt/cassandra ext4 defaults 0 2
```

e poi

```bash
sudo mount -a
```

che forza il refresh dei dischi e li monta nelle posizioni specificate.

In questo modo, i dischi verranno montati in automatico a ogni reboot del sistema.

Infine, creare le cartelle che serviranno a kafka, zookeeper e cassandra per scrivere i loro files:

```bash
sudo mkdir /mnt/kafka-zookeeper/data-kafka
sudo mkdir /mnt/kafka-zookeeper/data-zookeeper
sudo mkdir /mnt/kafka-zookeeper/logs-zookeeper

sudo mkdir /mnt/cassandra/data
```

## Creazione degli utenti e settaggio permessi sulle cartelle dati

Le cartelle create al punto precedente per Kafka, Zookeeper e Cassandra sono ancora di proprietà di `root`.
Bisogna quindi creare un nuovo gruppo di utenti, chiamato `simpss_group`, in cui inserire l'utente `user_simpss` (quello di login), e assegnare al gruppo le cartelle:

```bash
# creazione gruppo utenti
sudo groupadd simpss_group

# aggiungi l'utente al gruppo
sudo usermod -a -G simpss_group user_simpss
```

Fatto ciò, fare logout e login da SSH. Poi, cambiare il group owner delle cartelle:


```bash
sudo chgrp -R simpss_group /mnt/kafka-zookeeper/data-kafka/
sudo chmod -R g+rwx /mnt/kafka-zookeeper/data-kafka/

sudo chgrp -R simpss_group /mnt/kafka-zookeeper/data-zookeeper/
sudo chmod -R g+rwx /mnt/kafka-zookeeper/data-zookeeper/

sudo chgrp -R simpss_group /mnt/kafka-zookeeper/logs-zookeeper/
sudo chmod -R g+rwx /mnt/kafka-zookeeper/logs-zookeeper/

sudo chgrp -R simpss_group /mnt/cassandra/data/
sudo chmod -R g+rwx /mnt/cassandra/data/
```

## Installazione della versione corretta di Python (richiesta 3.7)

Visto che è richiesta la 3.7 e di default c'è la 3.6, utilizzare i seguenti comandi:

```bash
sudo add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) universe"
sudo apt-get update
sudo apt-get install python3.7 python3.7-dev
```

Poi installare `Pipenv` con `python3.7 -m pip install --user pipenv`.

Da terminale, navigare nella cartella del progetto e digitare `pipenv --python 3.7` per creare l'ambiente virtuale, poi ancora `pipenv install -r requirements.txt` e `pipenv install -r dev-requirements.txt`.

## Test di funzionamento

1. collegarsi in remoto con `ssh user_simpss@88.149.215.117 -p 2200`
2. assicurarsi che i dischi per kafka/zookeeper e cassandra siano montati: `ls /mnt` si **devono** trovare i mountpoint `/mnt/kafka-zookeeper` e `/mnt/cassandra`. Se ciò non è avvenuto, riferirsi agli step precedenti
3. `docker-compose rm -f`
4. `docker-compose pull` e aspettare che scarichi le immagini
5. `docker-compose up --build -d`
6. attivare la shell Pipenv con `pipenv shell` e fare lo stress test con:
    1. `python stress-sensor.py`
    2. `python stress_producer.py`
    3. `python stress_cassandra.py`
    4. entrare in un container Docker per fare le query a Cassandra con `docker run -it --network unimibsimpss_simpss-net --link cassandra1:cassandra --rm cassandra:3.11 cqlsh cassandra`
    5. nella shell che si presenta, digitare `SELECT * from simpss.sensor_data LIMIT 10;` e verficare che siano salvati i dati
6. una volta finito, `docker-compose down`

## Lancio del sistema

Per lanciare il sistema bisogna svolgere 4 operazioni: definire le associazioni tra sensori e gruppi, lanciare docker, lanciare il collegamento tra MQTT e Kafka (`link_mqtt_kafka.py`), e lanciare il collegamento tra Kafka e Cassandra (`link_kafka_cassandra.py`).

### Step 1: associazione sensori-gruppi

I sensori **devono** far parte ognuno di **un solo gruppo**. L'associazione si trova nel file `sensor_group.csv`, dove la prima colonna contiene l'id del sensore (type: `int`) e la seconda il nome del gruppo (type: `string`).

**Importante 1**: non sono ammessi id sensore duplicati, né righe/colonne mancanti nel file di definizione dell'associazione, né nomi di gruppi contenenti virgole.

**Importante 2**: il file va modificato **prima** di lanciare gli script Python, poiché essi lo caricano solo all'inizio dell'esecuzione e mai più. Se si effettuano modifiche al file, fermare e rilanciare gli script come descritto nelle prossime sezioni.

### Step 1: docker

1. collegarsi in remoto con `ssh user_simpss@88.149.215.117 -p 2200`
2. assicurarsi che i dischi per kafka/zookeeper e cassandra siano montati: `ls /mnt` si **devono** trovare i mountpoint `/mnt/kafka-zookeeper` e `/mnt/cassandra`. Se ciò non è avvenuto, riferirsi agli step precedenti
3. `docker-compose rm -f`
4. `docker-compose pull` e aspettare che scarichi le immagini
5. `docker-compose up --build -d`

### Step 2: collegare Kafka e Cassandra

1. collegarsi tramite ssh con `ssh user_simpss@88.149.215.117 -p 2200` ed entrare nella cartella del progetto con `cd unimib-simpss`
2. digitare il comando `screen` e premere invio alla schermata successiva. Si è ora in un terminale virtuale che continuerà a vivere anche dopo la nostra disconnessione (è quello che vogliamo visto che gli script Python devono girare sempre)
3. attivare la shell Pipenv con `pipenv shell`. Il terminale visualizzerà `(unimib-simpss)` prima del solito prompt
4. attivare il link tra Kafka e Cassandra con `python link_kafka_cassandra.py`

Il terminale resta quindi bloccato.
Per sbloccarlo, uscire dalla sessione di *screen* con il comando `Ctrl-a d`, ci si troverà nel terminale normale ancora collegati in SSH, ma non bloccati. 

Per riconnettersi al terminale virtuale che sta eseguendo lo script Python, digitare `screen -ls` e poi scegliere dalla lista una sessione con la dicitura `Detached`.
Prendere il suo id (qualcosa di simile a `357.pts-1.data`) e digitare `screen -r id_sessione`. Ci si troverà connessi di nuovo con lo script in esecuzione e i log visualizzati a schermo.

Per fermare lo script, semplicemente usare `Ctrl-c`.


### Step 3: collegare MQTT e Kafka

1. collegarsi tramite ssh con `ssh user_simpss@88.149.215.117 -p 2200` ed entrare nella cartella del progetto con `cd unimib-simpss`
2. digitare il comando `screen` e premere invio alla schermata successiva. Si è ora in un terminale virtuale che continuerà a vivere anche dopo la nostra disconnessione (è quello che vogliamo visto che gli script Python devono girare sempre)
3. attivare la shell Pipenv con `pipenv shell`. Il terminale visualizzerà `(unimib-simpss)` prima del solito prompt
4. attivare il link tra MQTT e Kafka con `python link_mqtt_kafka.py`

Il terminale resta quindi bloccato.
Per sbloccarlo, uscire dalla sessione di *screen* con il comando `Ctrl-a d`, ci si troverà nel terminale normale ancora collegati in SSH, ma non bloccati. 

Per riconnettersi al terminale virtuale che sta eseguendo lo script Python, digitare `screen -ls` e poi scegliere dalla lista una sessione con la dicitura `Detached`.
Prendere il suo id (qualcosa di simile a `357.pts-1.data`) e digitare `screen -r id_sessione`. Ci si troverà connessi di nuovo con lo script in esecuzione e i log visualizzati a schermo.

Per fermare lo script, semplicemente usare `Ctrl-c`.

Un buon tutorial su come usare `screen` si trova a [questo link](https://www.rackaid.com/blog/linux-screen-tutorial-and-how-to/).


## Spegnimento del sistema

Per spegnere il sistema, basta collegarsi agli `screen` remoti e usare `Ctrl-c`.

Per uscire dalla shell Pipenv usare `Ctrl-d`, così come dal terminale virtuale `screen`.

Per arrestare i Docker containers di MQTT, Kafka e Cassandra, entrare nella cartella del progetto `cd unimib-simpss` ed eseguire il comando `docker-compose down`.

In caso di problemi, si possono vedere i log con `docker-compose logs`.


# Troubleshooting

## Problema connessione SSH

Se la connessione viene rifiutata è colpa del firewall di MGH. In questo caso, prima di connettersi, nel terminale locale eseguire

```bash
ssh-keygen -R [88.149.215.117]:2200
```

che rimuove la vecchia chiave (apparentemente cambia ad ogni connessione, non so perché)

## Problemi di spazio su disco sul server

Conviene controllare periodicamente lo spazio disponibile nelle partizioni dati di Kafka e Cassandra. Un facile comando è `df -h`.
