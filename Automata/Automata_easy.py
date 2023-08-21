import datetime
import json
from paho.mqtt.client import Client

_states = [1, 0]
_G_index = 0
_Time_elapsed = 0


def on_message(client, userdata, msg):
    global _states, _Time_elapsed, _G_index
    rcv = json.loads(msg.payload)
    print(f"Message received from {rcv[3]}: {rcv[0:3]}", )

    if rcv[0]:
        _states = [0, 1]
        _G_index += rcv[1]
    else:
        _states = [1, 0]

    _Time_elapsed += rcv[2]

    print(f"status={_states}, G={_G_index}, T={datetime.timedelta(minutes=_Time_elapsed)}\n")


def on_connect(client, userdata, flags, rc):
    print("Connected!\n"
          "---------------------------------------------------\n"
          "log started:\n")


def halt():
    subscriber.loop_stop()
    print("Exiting...\n")
    exit(0)

def hoss_autoconfig():
    payload = {"device": "Plant",
               "name": "Simple plant",
               "manufacturer": "Max's industries"
               }
    subscriber.publish(topic="homeassistant/sensor/temperature/config", payload=json.dumps(payload))

if __name__ == '__main__':
    # Let's start with a clean screen!
    print("\033c")

    user = "Automata"

    subscriber = Client(user, clean_session=False)
    subscriber.on_message = on_message
    subscriber.on_connect = on_connect

    try:
        subscriber.connect("localhost")
        subscriber.subscribe("plant")
        subscriber.loop_forever(retry_first_connection=True)
        hoss_autoconfig()
    except ConnectionError as e:
        print(f"Network error:\n\t {e}")
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
