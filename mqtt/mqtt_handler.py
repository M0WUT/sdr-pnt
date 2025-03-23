# Standard imports
import logging
import socket
import json
from json.decoder import JSONDecodeError
from queue import Queue
from typing import Callable

# Third-party imports
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

# Local imports
from m0wut_drivers.linux_cpu import get_mac_address


class MqttHandler:
    def __init__(
        self,
        broker_ip_address: str,
        broker_port: int,
        node_name: str,
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
            x = {"mac": get_mac_address(), "name": f"{self.name}"}  # @TODO
            self.client.will_set("/discovery/lwt", json.dumps(x))
            self.client.connect(
                self.broker_ip_address, self.broker_port, keepalive=5
            )
            self.client.loop_start()

        except (socket.timeout, ConnectionRefusedError):
            self.logger.error(
                f"Broker not found at at {self.broker_ip_address}:{self.broker_port}",
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
                f"{self.broker_ip_address}:{self.broker_port}",
            )
        else:
            self.logger.error(
                "Failed to connect to broker at "
                f"{self.broker_ip_address}:{self.broker_port}",
            )
            pass  # @TODO

    def on_message(self, client, userdata, msg) -> None:
        # This is called in a seperate thread so put message on queue
        # and let message handler deal with it
        if msg.topic in self.callbacks.keys():
            self.message_queue.put(msg)
        else:
            self.logger.warning(
                f"No handler registered for subscribed topic: {msg.topic}",
            )

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
            self.logger.warning(
                source_node_id, __name__, "Malformed message received"
            )

        except JSONDecodeError:
            self.logger.warning(
                "Received message contains invalid JSON",
            )
        except KeyError as e:
            self.logger.warning(
                "Response from device " f"was not complete. Expected key: {e}",
            )

    def publish(self, topic: str, payload: str) -> None:
        self.logger.debug(f"Publishing MQTT: [{topic}] {payload}")
        self.client.publish(topic, payload)

    def register_callback(self, topic: str, func: Callable) -> None:
        assert (
            topic not in self.callbacks.keys()
        ), f"Topic: {topic} already has a callback function registered"
        error, _ = self.client.subscribe(topic)
        if error != mqtt.MQTT_ERR_SUCCESS:
            self.logger.error(
                f"Failed to subscribe to topic {topic}",
            )

        else:
            self.callbacks[topic] = func

            self.logger.info(
                self.name, __name__, f"Subscribed to MQTT topic: {topic}"
            )

    def remove_callback(self, topic: str) -> None:
        assert topic in self.callbacks.keys(), (
            f"Attempted to remove topic ({topic}) that's not "
            "currently subscribed to"
        )

        error, _ = self.client.unsubscribe(topic)
        if error != mqtt.MQTT_ERR_SUCCESS:
            self.logger.error(f"Failed to unsubscribe from topic {topic}")

        else:
            self.callbacks.pop(topic)
            self.logger.info(
                self.name, __name__, f"Unsubscribed from MQTT topic: {topic}"
            )

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.client.loop_stop()
        # Don't clean disconnect so LWT gets broadcast
        # self.client.disconnect()
        self.logger.info(
            f"Disconnected from MQTT Server {self.broker_ip_address}:{self.broker_port}",
        )
