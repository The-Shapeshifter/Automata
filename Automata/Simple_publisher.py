import json
import ssl
import time

from paho import mqtt
from paho.mqtt.client import Client


def on_publish(client, userdata, mid):
    print(f"Message published")


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


if __name__ == "__main__":
    user = "Automata"
    params, subscriber = ext_login_tls_config()
    subscriber.username_pw_set(params.get("username"), params.get("password"))
    subscriber.tls_set(ca_certs=params.get("cert_tls"), tls_version=2, cert_reqs=ssl.CERT_NONE)
    subscriber.connect(
        host=params.get("host"),
        port=params.get("port"),  # default 1883, per tls/ssl 8883
        keepalive=60
    )
    subscriber.subscribe(topic=params.get("rcv-topic"))

    subscriber.loop_start()
    # light, temp, mins
    payload = {
        "Date_Time": "18/11/2021 18:00",
        "Barometer_HPa": "1025.4",
        "Temp__C": "11.2",
        "HighTemp__C": "11.4",
        "LowTemp__C": "11.2",
        "Hum__": "93",
        "DewPoint__C": "10.1",
        "WetBulb__C": "10.5",
        "WindSpeed_Km_h": "3.2",
        "WindDirection": "WNW",
        "WindRun_Km": "0.8",
        "HighWindSpeed_Km_h": "6.4",
        "HighWindDirection": "WNW",
        "WindChill__C": "11.2",
        "HeatIndex__C": "11.3",
        "THWIndex__C": "11.3",
        "THSWIndex__C": "9.9",
        "Rain_Mm": "0",
        "RainRate_Mm_h": "0",
        "SolarRad_W_m_2": "0",
        "SolarEnergy_Ly": "0",
        "HighSolarRad_W_m_2": "0",
        "ET_Mm": "0",
        "UVIndex": "--",
        "UVDose_MEDs": "--",
        "HighUVIndex": "--",
        "HeatingDegreeDays": "0.075",
        "CoolingDegreeDays": "0"
    }

    subscriber.publish(topic=params.get("rcv-topic"), payload=json.dumps(payload))
    subscriber.loop_stop()
