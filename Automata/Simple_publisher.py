import json
import time

from paho.mqtt.client import Client


def on_publish(client, userdata, mid):
    print(f"Message published")


if __name__ == "__main__":
    username = "Publisher_test"
    _time = time.time()
    client = Client(username)
    client.on_publish = on_publish

    client.connect("localhost")
    client.loop_start()
    # light, temp, mins
    client.publish(topic="plant", payload=json.dumps([True, 25, 15, username]))

    # payload = {"unique_id": "plant_sensor_TEST",
    #            "name": "Plant sensor TEST",
    #            "state_topic": "plant/TestSensor",
    #            "availability_topic": "plant/TestSensor/status",
    #            "availability_mode": "any",
    #            "unit_of_measurement": "°C",
    #            "payload_available": "online",
    #            "suggested_display_precision": 1,
    #            "payload_not_available": "offline",
    #            "qos": 0,
    #            "retain": True
    #            }
    # client.publish(topic="homeassistant/sensor/temperature/config", payload=json.dumps(payload))
    # payload = {"name": "Automata",
    #            "state_topic": "automata",
    #            "unique_id": "Automata 2",
    #            "availability_topic": "plant/automata/status",
    #            "payload_available": "online",
    #            "payload_not_available": "offline",
    #            "dev": {
    #                "identifiers": "Automata 2 test",
    #                "manufacturer": "Optox dev",
    #                "model": "model",
    #                "name": "Automata MQTT",
    #                "sw_version": "1.0"
    #                 }
    #            }
    # client.publish(topic="homeassistant/event/automata/config", payload=json.dumps(payload))
    client.loop_stop()
