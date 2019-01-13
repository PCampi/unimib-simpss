# VerneMQ configuration

Le opzioni di configurazione sono quelle prese dal sito, per configurarlo su Docker basta aggiungere `DOCKER_VERNEMQ_XXX` dove `XXX` è il nome di una variabile di configurazione di VerneMQ.

Ad esempio, se volessi permettere il pub/sub di client anonimi senza autorizzazione, l'opzione rilevante sarebbe `allow_anonymous=on`, con Docker si dà in variabile d'ambiente `DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on`.

## Configurazioni rilevanti - Messaggi

Le seguenti opzioni sono quelle più rilevanti per i messaggi e le connessioni.

- `max_inflight_messages = 20`: massimo numero di messaggi con QoS 1 o 2 che possono essere in flight in un dato momento. Docker `DOCKER_VERNEMQ_MAX_INFLIGHT_MESSAGES`.
- `max_online_messages = 1000`: numero massimo di messaggi in coda, oltre a quelli che sono al momento in viaggio. Per no limit scegliere `-1`. Docker `DOCKER_VERNEMQ_MAX_ONLINE_MESSAGES`.
- `max_offline_messages = 1000`: numero massimo di messaggi con QoS 1 o 2 da mantenere nella coda offline. Per no limit scegliere `-1`. Docker `DOCKER_VERNEMQ_MAX_OFFLINE_MESSAGES`.
- `listener.tcp.allowed_protocol_versions = 3,4,`: versioni del protocollo MQTT supportato. Con il default, supporta la versione `3.1`, `3.1.1`. Se si vuole anche la `5.0`, inserire un `5` nella lista.
- `listener.tcp.default = 127.0.0.1:1883`: porta di default per il listener TCP.
- `message_size_limit = 0`: massima dimensione di un messaggio in *bytes*. Il default di 0 vuol dire che tutti i messaggi sono accettati. Il limite massimo per il protocollo MQTT è 268435455 bytes.


## Configurazioni rilevanti - Logging

Tipicamente il livello di logging è `INFO`.

- `log.console = off | file | console | both`: scelta se fare logging su console, su file o su entrambi. Se scelto un file, bisogna anche configurare `log.console.file`.
- `log.console.file = /path/to/log/file`: percorso del file di logging. Default a `/var/log/vernemq/console.log`.
- `log.error = on | off` e `log.error.file = /path/to/log/file`: file dove loggare gli errori. Default a `/var/log/vernemq/error.log`.
- `log.crash = on | off` e `log.crash.file = /path/to/log/file`: file dove loggare i crash. Default a `/var/log/vernemq/crash.log`. VerneMQ utilizza *rotazione* dei log di crash, effettuata alle `00:00` oppure al superamento di un threshold di dimensione del file, specificabile con `log.crash.size = 10MB` usando un valore a piacere.


## Load balancing di consumers

Accade quando un consumer non riesce a stare dietro alla quantità di messaggi che gli arrivano. In questo caso, se due o più consumers hanno lo stesso `ClientId`, VerneMQ può bilanciare il carico con le opzioni:

- `allow_multiple_sessions = on`
- `queue_deliver_mode = balance`


## Plugins

Ce ne sono per tutti i gusti.
Quelli di default sono visibili con il comando da shell

```bash
vmq-admin plugin show
```

Per abilitarne uno, utilizzare il comando

```bash
vmq-admin plugin enable --name=vmq_acl
```

Per disabilitarne uno, utilizzare il comando

```bash
vmq-admin plugin disable --name=vmq_acl
```

Posso configurare di default l'abilitazione o meno di un plugin, con la sintassi `plugins.nome_plugin = on`, per esempio `plugins.vmq_passwd = on`.
Se il plugin è esterno, posso specificare il suo path con `plugins.nome_plugin.path = /path/to/plugin`.

## Settare variabili ambiente in Docker

Alcune variabili di configurazione contengono il punto, per esempio quella appena vista `plugins.nome_plugin.path = /path/to/plugin`. In questo caso, utilizzare al posto del punto un doppio underscore:

`plugins.nome_plugin.path = /path/to/plugin` --> `DOCKER_VERNEMQ_PLUGINS__NOME_PLUGIN__PATH=/path/to/plugin`


# Shared subscription

L'ideale sarebbe che, anche con più Kafka Producers connessi a VerneMQ, un messaggio fosse ricevuto soltanto da uno di essi. C'è un'opzione che si chiama Shared Subscription, per cui i consumers MQTT (cioè per noi i Kafka Producers) possono consumare il topic `$share/sharename/topic`. In questo caso, si assicura che VerneMQ manderà un messaggio a uno soltanto di essi.

Bisogna settare la policy di sharing, con la variabile


```bash
shared_subscription_policy = local_only | random | prefer_local
```

Utilizzare il valore `random` per i nostri scopi.


## LevelDB storage

Per storage di messaggi a backend, VerneMQ usa LevelDB. Bisogna solo configurare la quantità massima di RAM in percentuale da dare a LevelDB.

Attenzione: probabilmente la userà tutta e occhio ai warings e agli errori di Out-Of-Memory.

`leveldb.maximum_memory.percent = 20` --> `DOCKER_VERNEMQ_LEVELDB__MAXIMUM_MEMORY__PERCENT=20`.


# Monitoring con Graphite

Le configurazioni sono queste:

```bash
graphite_enabled = on
graphite_host = QUI METTERE L'HOST!!!
graphite_port = 2003
graphite_interval = 20000
graphite_api_key = YOUR-GRAPHITE-API-KEY
graphite.interval = 15000 <-- BOH!

# set the connect timeout (defaults to 5000 ms)
graphite_connect_timeout = 10000

# set a reconnect timeout (default to 15000 ms)
graphite_reconnect_timeout = 10000

# set a custom graphite prefix (defaults to '')
graphite_prefix = vernemq
```