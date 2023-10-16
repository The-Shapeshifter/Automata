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
    try:
        client = ntplib.NTPClient()
        response = client.request("it.pool.ntp.org", version=3)
        time = datetime.strptime(ctime(response.tx_time), "%a %b %d %H:%M:%S %Y")
    except Exception as ex:
        print(f"Error while retrieving NTP time: {ex}\n"
              f"defaulting to local date\n")
        logging.error(f"Error while retrieving NTP time: {ex}\n"
                      f"defaulting to local date\n")
        time = datetime.utcnow()

    if init:
        _Prev_rcv_time = time
        print(f"Server started, Local time: {_Prev_rcv_time}\n"
              f"Connecting to broker...\n")
        logging.info(f"Server started")
    return time


def time_calculation(msg_time: str) -> None:
    global _Prev_rcv_time, _Time_elapsed, _Is_hour_passed, _Init
    msg_time = datetime.strptime(msg_time, '%d/%m/%Y %H:%M')
    _Time_elapsed = msg_time - _Prev_rcv_time
    _Prev_rcv_time = msg_time

    if _Init:
        _Is_hour_passed = 0
        _Init = False
    else:
        _Is_hour_passed += divmod(_Time_elapsed.seconds, 60)[0]


def hoss_autoconfig():
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

    rad = float(message.get('SolarRad_W_m_2'))
    _Rad_sum += rad
    temp = float(message.get("Temp__C"))
    _Temp_sum += temp
    subscriber.publish(topic="plant/temp", payload=message.get("Temp__C"))
    subscriber.publish(topic="plant/humidity", payload=message.get("Hum__"))
    _Msg_counter += 1

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

    subscriber.publish(topic='plant/state', payload=_Current_state.name)
    subscriber.publish(topic='plant/N_val', payload=N)
    subscriber.publish(topic='plant/Bio_val', payload=Bio)
    subscriber.publish(topic='plant/LAI_h_val', payload=LAI_h)
    subscriber.publish(topic='plant/Wf_val', payload=Wf)
    subscriber.publish(topic='plant/Wm_val', payload=Wm)

    match rad > 0:
        case True:
            subscriber.publish(topic='plant/light', payload='on')
        case False:
            subscriber.publish(topic='plant/light', payload='off')


def on_message(client, userdata, msg) -> None:
    global _Current_state, _Time_elapsed, _Prev_rcv_time, _Is_hour_passed

    message = json.loads(msg.payload.decode("utf-8"))
    # print(f"\t{json.dumps(message)}")

    time_calculation(message.get("Date_Time"))
    current_time = set_current_time()

    print(f"Message received on {current_time}:")
    print(f"\tTime Elapsed since last message: {_Time_elapsed}")
    print(f"\tHour counter: {_Is_hour_passed}")

    # Funzione per i passaggi di stato nell'automa
    state_transition(message)
    print(f"\tCurrent state: {_Current_state.name}\n")


def on_connect(client, userdata, flags, rc) -> None:
    print("Connected!\n"
          "---------------------------------------------------\n")


def on_log(client, userdata, level, buf):
    logging.debug(buf)


def halt() -> None:
    print("Deactivating all sensor on HA...")
    with open("./config/config.json", "r") as json_file:
        mqtt_config = json.load(json_file)
    for sensor in mqtt_config["sensors"]:
        subscriber.publish(topic=sensor["availability_topic"], payload='offline')
    subscriber.loop_stop()
    shutil.copyfile('./logs/Automata.log', './logs/Automata_old.log')
    print("Done\nExiting...\n")
    exit(0)


if __name__ == '__main__':
    # Let's start with a clean screen!
    print("\033c")

    if not os.path.exists('./logs'):
        os.makedirs('./logs')

    logging.basicConfig(format='Date-Time : %(asctime)s %(levelname)s - %(message)s',
                        level=logging.DEBUG,
                        filename='logs/Automata.log', filemode='w')

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
        hoss_autoconfig()
        subscriber.loop_forever(retry_first_connection=True)
    except Exception as e:
        print(f"Error:\t {e}")
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
