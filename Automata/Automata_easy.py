import signal
from paho.mqtt.client import Client

_status = [[], []]


def on_message(client, userdata, msg):
    print(f"{user} --> {msg.payload.decode()}")


def on_connect(client, userdata, flags, rc):
    print("Connected!\n"
          "---------------------------------------------------\n"
          "log started:\n")


def halt():
    subscriber.loop_stop()
    print("Exiting...\n")
    exit(0)


if __name__ == '__main__':
    # Let's start with a clean screen!
    print("\033c")

    user = input("Input username: ")

    subscriber = Client(user, clean_session=False)
    subscriber.on_message = on_message
    subscriber.on_connect = on_connect

    try:
        subscriber.connect("localhost")
        subscriber.subscribe("temp")
        subscriber.loop_forever(retry_first_connection=True)
    except ConnectionError as e:
        print(f"Network error:\n\t {e}")
        exit(1)
    except KeyboardInterrupt:
        print("---------------------------------------------------\n"
              "Ctrl+c detected\n")
        halt()
