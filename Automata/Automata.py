import json
import logging
import os
import shutil
import ssl
from datetime import datetime, timedelta
from time import ctime

import ntplib
from paho import mqtt
from paho.mqtt.client import Client

import Transitions
from States import States

_Current_state = States.S0
_Prev_rcv_time = timedelta()
_Time_elapsed = timedelta()
_Is_hour_passed = 0
_Msg_counter = 0
_Rad_sum = 0.0
_Temp_sum = 0.0
_Init = True
_MAX_WAIT_TIME = 60
N = 0
Bio = 0
LAI_h = 0
Wf = 0
Wm = 0


def set_current_time(init=False) -> datetime:
    global _Prev_rcv_time

    # Al fine di un debug più funzionale e per rendere localizzato il log, si utilizza l'ora locale
    # questo permette di dare un senso all'ordine degli eventi nei log rendendolo indipendente da errori della macchina
    # e da quelli del timestamp dei messaggi (che viene comunque salvato)
    try:
        client = ntplib.NTPClient()
        response = client.request("it.pool.ntp.org", version=3)
        time = datetime.strptime(ctime(response.tx_time), "%a %b %d %H:%M:%S %Y")
    except Exception as ex:

        # Se per qualche ragione i server NTP non sono raggiungibili, di default si usa l'ora locale della macchina
        print(f"Error while retrieving NTP time: {ex}\n"
              f"defaulting to local date\n")
        logging.error(f"Error while retrieving NTP time: {ex}\n"
                      f"defaulting to local date\n")
        time = datetime.utcnow()

    if init:
        # Solo per l'avvio, si prende in considerazione l'ora reale, questo verrà successivamente modificato con
        # il confronto tra il timestamp precedente e quello successivo dei messaggi per calcolarne il tempo
        # di arrivo
        _Prev_rcv_time = time
        print(f"Server started, Local time: {_Prev_rcv_time}\n"
              f"Connecting to broker...\n")
        logging.info(f"Server started")
    return time


def time_calculation(msg_time: str) -> None:
    global _Prev_rcv_time, _Time_elapsed, _Is_hour_passed, _Init

    # come suggerisce il nome, calcola il tempo passato dall'ultimo messaggio, confrontandolo con il timestamp
    # del messaggio corrente: utile per debuggare grossi ritardi di rete o malfunzionamenti
    msg_time = datetime.strptime(msg_time, '%d/%m/%Y %H:%M')
    _Time_elapsed = msg_time - _Prev_rcv_time
    _Prev_rcv_time = msg_time

    # TODO: inserire un confronto con l'ora locale, attualmente non attivo in quanto i messaggi risalgono a 2 anni fa

    # Per motivi di funzionamento relativi a incongruenze orarie, se il programma è appena partito il tempo passato è
    # ovviamente 0 minuti
    if _Init:
        _Is_hour_passed = 0
        _Init = False
    else:
        _Is_hour_passed += divmod(_Time_elapsed.seconds, 60)[0]


def hoss_autoconfig():
    # Molto semplice: prelevo i sensori dal file json presente in config, ne faccio il parsing e invio il necessario
    # ad hass che si occuperà in autonomia della generazione delle proprie configurazioni interne e della appropriata
    # visualizzazione, configurata anch'essa in alcuni casi dentro il json
    with open("./config/config.json", "r") as json_file:
        mqtt_config = json.load(json_file)
    for sensor in mqtt_config["sensors"]:
        topic = sensor["autoconf_topic"]
        # Rimuovi il campo "autoconf_topic" prima di inviare la configurazione
        del sensor["autoconf_topic"]
        payload = json.dumps(sensor)
        logging.info(f"sent autoconf to: {topic}: {payload}")
        subscriber.publish(topic=topic, payload=payload)
        subscriber.publish(topic=sensor["availability_topic"], payload='online')


def ext_login_tls_config():
    par = {
        "host": "90.147.167.187",
        "port": 8883,
        "login": True,
        "username": "homeassistant",
        "password": "univr_agri01",
        "rcv-topic": "sensori",
        "send-topic": "prova2",
        "cert_tls": "ca-root-cert.crt"
    }

    sub = Client(
        client_id=user,
        clean_session=True,
        userdata=None,
        protocol=mqtt.client.MQTTv311,
        transport='tcp'
    )

    return par, sub


def state_transition(message: dict) -> None:
    global _Current_state, _Msg_counter, _Rad_sum, _Temp_sum, _Is_hour_passed, N, Bio, LAI_h, Wf, Wm

    # Questo è il cuore del sistema: i valori nel messaggio vengono presi e sistemati: in questa prima parte
    # vengono accumulati rad e temp per i quali è richiesta la media oraria nelle funzioni di transizione
    rad = float(message.get('SolarRad_W_m_2'))
    _Rad_sum += rad
    temp = float(message.get("Temp__C"))
    _Temp_sum += temp
    subscriber.publish(topic="plant/temp", payload=message.get("Temp__C"))
    subscriber.publish(topic="plant/humidity", payload=message.get("Hum__"))
    _Msg_counter += 1

    # _MAX_WAIT_TIME è il tempo di attesa prima di passare i valori allàinterno della funzione di transizione,
    # attualmente impostato a 60 (minuti)
    # se siamo a quel valore o oltre, si passa dentro la funzione, si calcolano i vari valori e si resettano
    # tutti gli accumulatori per ricominciare l'attesa

    if _Is_hour_passed >= _MAX_WAIT_TIME:
        _Current_state, N, Bio, LAI_h, Wf, Wm = Transitions.states_transition(
            _Current_state,
            _Temp_sum / _Msg_counter,
            _Rad_sum / _Msg_counter)
        _Is_hour_passed = 0
        _Temp_sum = 0
        _Rad_sum = 0
        _Msg_counter = 0
        print(f"\tCalling state transition function...")
        logging.info("Calling state transition function...")

    # Ad ogni ciclo, anche come metodo di keepalive, vengono reinviati i valori di ogni variabile ad HASS
    # Questa operazione occupa poca banda e poca CPU ma volendo è possibile migliorarne le performance inserendo
    # i publish all'iterno dell'if
    subscriber.publish(topic='plant/state', payload=_Current_state.name)
    subscriber.publish(topic='plant/N_val', payload=N)
    subscriber.publish(topic='plant/Bio_val', payload=Bio)
    subscriber.publish(topic='plant/LAI_h_val', payload=LAI_h)
    subscriber.publish(topic='plant/Wf_val', payload=Wf)
    subscriber.publish(topic='plant/Wm_val', payload=Wm)

    # Piccolo QoF sul quale ci sarebbe da fare tuning: indico se c'è luce o buio
    match rad > 0:
        case True:
            subscriber.publish(topic='plant/light', payload='on')
        case False:
            subscriber.publish(topic='plant/light', payload='off')


def on_message(client, userdata, msg) -> None:
    global _Current_state, _Time_elapsed, _Prev_rcv_time, _Is_hour_passed

    # All'arrivo di un messaggio, on message si preoccupa di fare tutte le operazioni di smistamento di questo,
    # viene calcolata la differenza tra l'ora di ricezione e quella dell'ultimo messaggio e vengono stampate le
    # statistiche, successivamente il messaggio viene inviato alla funzione di transizione che fa il resto

    message = json.loads(msg.payload.decode("utf-8"))

    time_calculation(message.get("Date_Time"))
    current_time = set_current_time()

    print(f"Message received on {current_time}:")
    print(f"\tTime Elapsed since last message: {_Time_elapsed}")
    print(f"\tHour counter: {_Is_hour_passed}")

    # Funzione per i passaggi di stato nell'automa
    state_transition(message)
    print(f"\tCurrent state: {_Current_state.name}\n")


def on_connect(client, userdata, flags, rc) -> None:
    # Se MQTT è correttamente connesso, stampa:
    print("Connected!\n"
          "---------------------------------------------------\n")


def on_log(client, userdata, level, buf):
    logging.debug(buf)


def halt() -> None:
    # Chiusura gracefull del programma, indica ad HASS che i sensori non sono più disponibili, crea una copia del log
    # e chiude tutto

    print("Deactivating all sensors on HA...")
    with open("./config/config.json", "r") as json_file:
        mqtt_config = json.load(json_file)
    for sensor in mqtt_config["sensors"]:
        subscriber.publish(topic=sensor["availability_topic"], payload='offline')
    subscriber.loop_stop()
    shutil.copyfile('./logs/Automata.log', './logs/Automata_old.log')
    print("Done\nExiting...\n")


if __name__ == '__main__':
    # Let's start with a clean screen!
    print("\033c")

    # Setup del sistema di logging

    if not os.path.exists('./logs'):
        os.makedirs('./logs')

    logging.basicConfig(format='Date-Time : %(asctime)s %(levelname)s - %(message)s',
                        level=logging.DEBUG,
                        filename='logs/Automata.log', filemode='w')

    # tutto il resto: ora locale, call back per MQTT personalizzate e inizializzazione del subscriber

    set_current_time(init=_Init)

    user = "Automata"

    params, subscriber = ext_login_tls_config()

    subscriber.on_message = on_message
    subscriber.on_connect = on_connect
    subscriber.on_log = on_log

    try:
        subscriber.username_pw_set(params.get("username"), params.get("password"))
        subscriber.tls_set(ca_certs=params.get("cert_tls"), tls_version=2, cert_reqs=ssl.CERT_NONE)
        subscriber.connect(
            host=params.get("host"),
            port=params.get("port"),  # default 1883, per tls/ssl 8883
            keepalive=60
        )
        subscriber.subscribe(topic=params.get("rcv-topic"))

        # Richiamo del metodo per la configurazione automatica dei sensori su hass
        hoss_autoconfig()

        # Finalmente, loop di attesa messaggi e stampa indicatrice della fine del setup
        subscriber.loop_forever(retry_first_connection=True)
    except Exception as e:

        # TODO: migliorare la gestione degli errori, questa non fa capire da dove arriva il problema
        print(f"Error:\t {e}")
        halt()
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
        exit(0)

# Il seguente automa con relativa integrazione ad HASS utilizzando MQTT è stato scritto come parte della mia tesi per
# la laurea triennale in informatica all'Universita di Verona.
# Si tratta della conclusione di tre anni sudati, faticosi e stressanti ma tuttavia amati e voluti come si vogliono i
# traguardi importanti quando si capisce di poterli raggiungere pur faticando, sudando e stressandosi.
#
# Desidero ringraziare Monica, per l'amore e il supporto implacabile che ho ricevuto in questi anni e
# che solo persone come lei sono in grado di dare nella loro unicità
#
# La mia famiglia che, nel bene e nel male, ha creduto nelle mie capacità e ha assistito al mio traguardo
#
# Ringrazio il professor Quaglia, senza il quale non avrei avuto l'aiuto necessario a chiudere le ultime parti
# di questo percorso e la realizzazione di questo progetto
#
# Paola, che mi ha tenuto la mano fino a quando ho potuto camminare da solo e mi darà ancora una mano nei momenti
# in cui camminerò storto
#
# Gianmaria, Andrea e Amos, aiutanti e compagni in questi anni di lacrime ed esami, senza i quali non sarei mai
# riuscito ad affrontare questo percorso di studi e che mi hanno insegnato più di quanto loro sapranno mai
#
# Infine ai miei amici, quelli rimasti e quelli andati che mi hanno dato il materiale grezzo per la mia crescita.
#
# ancora oggi così: A metà strada su una strada infinita.
#
# Grazie a tutti, di cuore, dal più profondo.
