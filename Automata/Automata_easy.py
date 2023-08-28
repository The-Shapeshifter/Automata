import datetime
import json
from States import States
from paho.mqtt.client import Client

_Current_state = States.NIGHTTIME
_G_index = 0
_Time_elapsed = datetime.timedelta(hours=0, minutes=0)


def on_message(client, userdata, msg) -> None:
    global _Current_state, _Time_elapsed, _G_index
    rcv = json.loads(msg.payload)
    print(f"Message received from {rcv[3]}: {rcv}")

    match rcv[0]:
        case True:
            _Current_state = States.DAYTIME
            _G_index += rcv[1]
        case False:
            _Current_state = States.NIGHTTIME
        case default:
            print("Error: no case match found")

    _Time_elapsed += datetime.timedelta(minutes=rcv[2])

    print(f"status= {_Current_state.name}, G= {_G_index}, T= {_Time_elapsed}\n")


def on_connect(client, userdata, flags, rc) -> None:
    print("Connected!\n"
          "---------------------------------------------------\n"
          "log started:\n")


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
        # hoss_autoconfig()
    except ConnectionError as e:
        print(f"Network error:\n\t {e}")
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
