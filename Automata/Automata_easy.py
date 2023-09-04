import json
import ssl
from time import ctime

import ntplib
from paho import mqtt
from States import States
from paho.mqtt.client import Client
from datetime import datetime, timedelta


_Current_state = States.NIGHTTIME
_G_index = 0
_Rcv_time = timedelta()
_Time_elapsed = timedelta(hours=0, minutes=0)


def set_current_time():
    global _Rcv_time
    server = "it.pool.ntp.org"
    try:
        client = ntplib.NTPClient()
        response = client.request(server, version=3)
        _Rcv_time = datetime.strptime(ctime(response.tx_time), "%a %b %d %H:%M:%S %Y")
    except Exception as e:
        print(f"Error while retrieving time from \"{server}\":")
        print(f"\t{e}")
        print("Defaulting to machine time\n")
        _Rcv_time = datetime.utcnow()

    print(f"Server started, Local time: {_Rcv_time}\n"
          f"Connecting to broker...\n")


def on_message(client, userdata, msg) -> None:
    global _Current_state, _Time_elapsed, _G_index, _Rcv_time

    message = json.loads(msg.payload.decode("utf-8"))
    print(f"\t{message}")

    subscriber.publish(
        topic=params.get("send-topic"),
        payload="Automata rcv OK"
        # retain=True
    )

    msg_time = datetime.strptime(message.get("Date_Time"), '%d/%m/%Y %H:%M')
    _Time_elapsed += msg_time - _Rcv_time
    _Rcv_time = msg_time
    print(f"\tTime Elapsed: {_Time_elapsed}")
    # rcv = json.loads(msg.payload)
    # print(f"Message received from {rcv[3]}: {rcv}")

    # match rcv[0]:
    #    case True:
    #        _Current_state = States.DAYTIME
    #        _G_index += rcv[1]
    #    case False:
    #        _Current_state = States.NIGHTTIME
    #    case default:
    #        print("Error: no case match found")

    # _Rcv_time += datetime.timedelta(minutes=rcv[2])

    # print(f"status= {_Current_state.name}, G= {_G_index}, T= {_Rcv_time}\n")


def on_connect(client, userdata, flags, rc) -> None:
    print("Connected!\n"
          "---------------------------------------------------\n"
          "log started:\n")


def on_log(client, userdata, level, buf):
    print("\tdev log: ", buf)


def halt() -> None:
    subscriber.loop_stop()
    print("Exiting...\n")
    exit(0)


def hoss_autoconfig():
    payload = {"device": "Plant",
               "name": "Simple plant",
               "manufacturer": "Max's industries"
               }
    subscriber.publish(topic="homeassistant/sensor/temperature/config", payload=json.dumps(payload))


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


if __name__ == '__main__':
    # Let's start with a clean screen!
    print("\033c")

    set_current_time()

    user = "Automata"

    params, subscriber = ext_login_tls_config()

    subscriber.on_message = on_message
    subscriber.on_connect = on_connect
    # subscriber.on_log = on_log

    try:
        subscriber.username_pw_set(params.get("username"), params.get("password"))
        subscriber.tls_set(ca_certs=params.get("cert_tls"), tls_version=2, cert_reqs=ssl.CERT_NONE)
        subscriber.connect(
            host=params.get("host"),
            port=params.get("port"),  # default 1883, per tls/ssl 8883
            keepalive=60
        )
        subscriber.subscribe(topic=params.get("rcv-topic"))
        subscriber.loop_forever(retry_first_connection=True)
        # hoss_autoconfig()
    except ConnectionError as e:
        print(f"Network error:\n\t {e}")
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
