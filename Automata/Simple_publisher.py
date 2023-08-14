import json

from paho.mqtt.client import Client


def on_publish(client, userdata, mid):
    print(f"Message published")


if __name__ == "__main__":
    client = Client("Publisher_test")
    client.on_publish = on_publish

    client.connect("localhost")

    # messaggio = input("Inserisci il testo da inviare al topic test")
    client.publish(topic="plant", payload=json.dumps([15, True]))

    client.disconnect()
