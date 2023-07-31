from queue import Queue

from paho.mqtt.client import Client


class MosquittoSub:
    _self = None
    _username = None
    _client = None
    queue = None

    # Singleton definition: the constructor assures that an instance already exists; if it doesn't it creates one
    # and assures that only one instance of the object exists
    def __new__(cls, username, queue):
        if cls._self is None:
            cls._self = super().__new__(cls)
        return cls._self

    # Initialization of the connection with the broker and threading start
    def __init__(self, username, queue):
        self._client = Client(username, False)
        self._username = username
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        self._client.on_connect_fail = self.on_connect_fail
        self.queue = queue

        try:
            self._client.connect("localhost")
        except ConnectionError as error:
            print("Error while connecting to broker:\n\t " + error.strerror)
            exit(error.errno)

        self._client.subscribe("test_topic")
        self._client.loop_start()   # Here is where the magic happens!

    def on_message(self, client, userdata, msg):
        self.queue.put([self._username, msg.payload.decode()])

    def on_connect(self, client, userdata, flags, rc):
        self.queue.put(True)

    def on_connect_fail(self, client, userdata):
        self.queue.put(False)
        exit(1)

    def halt(self):
        self._client.loop_stop()    # Here is where the magic stops!
        exit(0)
