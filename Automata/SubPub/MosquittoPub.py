from paho.mqtt.client import Client


class MosquittoPub:
    client = Client("Publisher_test")
    def on_publish(client, userdata, mid):
        print("Messaggio pubblicato")

    client.on_publish = on_publish

    client.connect("localhost")
    client.loop_start()

    #messaggio = input("Inserisci il testo da inviare al topic test")
    client.publish(topic="test_topic", payload="Test")

    client.loop_stop()
    client.disconnect()
