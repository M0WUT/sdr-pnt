# Standard imports
import logging
import socket
import json
from json.decoder import JSONDecodeError
from queue import Queue

# Third-party imports
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


class MqttHandler:
    def __init__(
        self, broker_ip_address: str, broker_port: int, node_name: str
    ):
        super().__init__()
        self.client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.broker_ip_address = broker_ip_address
        self.broker_port = broker_port
        self.name = node_name
        self.callbacks = {}
        self.message_queue = Queue()
        self.logger = logging.getLogger(__name__)

        try:
            x = {"mac": "00:00", "name": f"{self.name}"}  # @TODO
            self.client.will_set("/discovery/lwt", json.dumps(x))
            self.client.connect(
                self.broker_ip_address, self.broker_port, keepalive=5
            )
            self.client.loop_start()

        except (socket.timeout, ConnectionRefusedError):

            self.logger.error(
                f"Broker not found at at {self.broker_ip_address}:{self.broker_port}"
            )

    def tick(self) -> None:
        # This deliberately only deals with one thing at a time
        # Prevents locking up everything else if swamped with messages
        if not self.message_queue.empty():
            self.message_handler(self.message_queue.get())

    def on_connect(
        self, client, userdata, flags, reason_code, properties
    ) -> None:
        if reason_code == 0:
            self.logger.info(
                f"Successfully connected to MQTT Broker at "
                f"{self.broker_ip_address}:{self.broker_port}"
            )
        else:
            # self.warnings.add_error(
            #     self.name,
            #     "MQTT",
            #     "Failed to connect to broker at "
            #     f"{self.ipAddr}:{self.ipPort}",
            #     broadcast=False,
            # )
            pass  # @TODO

    def on_message(self, client, userdata, msg) -> None:
        # This is called in a seperate thread so put message on queue
        # and let message handler deal with it
        if msg.topic in self.callbacks.keys():
            self.message_queue.put(msg)
        else:
            # self.warnings.add_warning(
            #     self.name,
            #     "MQTT",
            #     f"No handler registered for subscribed topic: {msg.topic}",
            #     broadcast=False,
            # )
            pass  # @TODO

    def message_handler(self, msg: mqtt.MQTTMessage) -> None:
        message = msg.payload.decode("utf-8")
        self.logger.debug(f"Received MQTT: [{msg.topic}] {message}")
        try:
            source_node_id = "Unknown device"
            res = json.loads(message)
            if "name" in res.keys():
                source_node_id = res["name"]
            self.callbacks[msg.topic].func(res)

        except UnicodeDecodeError:
            # self.warnings.add_warning(id, "MQTT", "Malformed message received")
            pass  # @TODO
        except JSONDecodeError:
            # self.warnings.add_warning(
            #     id, "MQTT", "Received message contains invalid JSON"
            # )
            pass  # @TODO
        except KeyError as e:
            # self.warnings.add_warning(
            #     id,
            #     "MQTT",
            #     "Response from device "
            #     "was not complete. Expected key: {}".format(e),
            # )
            pass  # @TODO

    def publish(self, topic: str, payload: str) -> None:
        self.logger.debug(f"Publishing MQTT: [{topic}] {payload}")
        self.client.publish(topic, payload)

    def register_callback(self, topic: str, func: function) -> None:
        assert (
            topic not in self.callbacks.keys()
        ), f"Topic: {topic} already has a callback function registered"
        error, _ = self.client.subscribe(topic)
        if error != mqtt.MQTT_ERR_SUCCESS:
            # self.warnings.add_error(
            #     self.name,
            #     "MQTT",
            #     f"Failed to subscribe to topic {topic}",
            #     broadcast=False,
            # )
            pass  # @TODO
        else:
            self.callbacks[topic] = func

            self.logger.info(f"Subscribed to MQTT topic: {topic}")

    def remove_callback(self, topic: str) -> None:
        assert topic in self.callbacks.keys(), (
            f"Attempted to remove topic ({topic}) that's not "
            "currently subscribed to"
        )

        error, _ = self.client.unsubscribe(topic)
        if error != mqtt.MQTT_ERR_SUCCESS:
            # self.warnings.add_error(
            #     self.name,
            #     "MQTT",
            #     f"Failed to unsubscribe from topic {topic}",
            #     broadcast=False,
            # )
            pass  # @TODO
        else:
            self.callbacks.pop(topic)
            self.logger.info(f"Unsubscribed from MQTT topic: {topic}")

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.client.loop_stop()
        # Don't clean disconnect so LWT gets broadcast
        # self.client.disconnect()
        self.logger.info(
            f"Disconnected from MQTT Server {self.broker_ip_address}:{self.broker_port}"
        )
