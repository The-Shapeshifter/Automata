import json
import logging
import ssl
from datetime import datetime, timedelta
from time import ctime

import ntplib
from paho import mqtt
from paho.mqtt.client import Client

from States import States

_Current_state = States.NIGHTTIME
_G_index = 0
_Rcv_time = timedelta()
_Time_elapsed = timedelta()


def set_current_time(init=False) -> datetime:
    global _Rcv_time
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
        _Rcv_time = time
        print(f"Server started, Local time: {_Rcv_time}\n"
              f"Connecting to broker...\n")
        logging.info(f"Server started")
    return time


def time_calculation(msg_time: str) -> None:
    global _Rcv_time, _Time_elapsed
    msg_time = datetime.strptime(msg_time, '%d/%m/%Y %H:%M')
    _Time_elapsed = msg_time - _Rcv_time
    _Rcv_time = msg_time


def on_message(client, userdata, msg) -> None:
    global _Current_state, _Time_elapsed, _G_index, _Rcv_time

    message = json.loads(msg.payload.decode("utf-8"))
    # print(f"\t{json.dumps(message)}")

    subscriber.publish(
        topic=params.get("send-topic"),
        payload="Automata rcv OK"
        # retain=True
    )

    time_calculation(message.get("Date_Time"))
    current_time = set_current_time()

    print(f"Message received on {current_time}:")
    print(f"\tTime Elapsed since last message: {_Time_elapsed}")

    # Funzione per i passaggi di stato nell'automa
    state_transition(message)
    print(f"\tCurrent state: {_Current_state.name.lower()}\n")


def on_connect(client, userdata, flags, rc) -> None:
    print("Connected!\n"
          "---------------------------------------------------\n")


def on_log(client, userdata, level, buf):
    logging.debug(buf)


def halt() -> None:
    subscriber.loop_stop()
    print("Exiting...\n")
    exit(0)


def hoss_autoconfig():
    payload = {"name": "Photoperiod Sensor",
               "state_topic": "plant/light01",
               "unique_id": "LightSens01",
               "availability_topic": "plant/light01/status",
               "payload_available": "online",
               "payload_not_available": "offline",
               "payload_on": "on",
               "payload_off": "off",
               "device_class": "light",
               "dev": {
                   "identifiers": "Automata",
                   "manufacturer": "Optox dev",
                   "model": "null",
                   "name": "Automata MQTT",
                   "sw_version": "1.0"
                    }
               }
    subscriber.publish(topic="homeassistant/binary_sensor/light/config", payload=json.dumps(payload))
    subscriber.publish(topic="plant/light01/status", payload='online')

    payload = {"unique_id": "Temperature sensor",
               "name": "TempSens01",
               "state_topic": "plant/temp",
               "availability_topic": "plant/temp/status",
               "availability_mode": "latest",
               "unit_of_measurement": "°C",
               "payload_available": "online",
               "payload_not_available": "offline",
               "qos": 0,
               "retain": True,
               "dev": {
                   "identifiers": "Automata"
                    }
               }
    subscriber.publish(topic="homeassistant/sensor/temperature/config", payload=json.dumps(payload))
    subscriber.publish(topic="plant/temp/status", payload='online')

    payload = {"unique_id": "Humidity sensor",
               "name": "HumSens01",
               "state_topic": "plant/humidity",
               "availability_topic": "plant/humidity/status",
               "availability_mode": "latest",
               "unit_of_measurement": "%",
               "payload_available": "online",
               "payload_not_available": "offline",
               "qos": 0,
               "retain": True,
               "dev": {
                   "identifiers": "Automata"
                    }
               }
    subscriber.publish(topic="homeassistant/sensor/humidity/config", payload=json.dumps(payload))
    subscriber.publish(topic="plant/humidity/status", payload='online')


def ext_login_tls_config():
    par = {
        "host": "90.147.167.187",
        "port": 8883,
        "login": True,
        "username": "homeassistant",
        "password": "univr_agri01",
        "rcv-topic": "sensori",
        "send-topic": "prova2",
        "cert_tls": "ca-root-cert.crt",
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
    global _Current_state
    print(f"\tLight value: {int(message.get('SolarRad_W_m_2'))}")
    is_day_time = int(message.get('SolarRad_W_m_2')) > 0

    match is_day_time:
        case True:
            _Current_state = States.DAYTIME
            subscriber.publish(topic='plant/light01', payload='on')
        case False:
            _Current_state = States.NIGHTTIME
            subscriber.publish(topic='plant/light01', payload='off')

    subscriber.publish(topic="plant/temp", payload=message.get("Temp__C"))


if __name__ == '__main__':
    # Let's start with a clean screen!
    print("\033c")

    logging.basicConfig(format='Date-Time : %(asctime)s %(levelname)s - %(message)s',
                        level=logging.DEBUG,
                        filename='logs/Automata.log', filemode='w')

    set_current_time(init=True)

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
        print(f"Network error:\t {e}")
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
