# Standard imports
import logging
import socket
import json
from json.decoder import JSONDecodeError
from queue import Queue
from typing import Callable, Optional

# Third-party imports
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


# Local imports
from m0wut_drivers.linux_cpu import get_mac_address


class BrokerConnectionError(Exception):
    pass


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
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.broker_ip_address = broker_ip_address
        self.broker_port = broker_port
        self.node_name = node_name
        self.callbacks = {}
        self.message_queue = Queue()
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.mqtt_connected: bool = False

        try:
            self.client.will_set(
                "/status/discovery",
                json.dumps(
                    {
                        "mac_address": get_mac_address(),
                        "node_name": f"{self.node_name}",
                        "status": "disconnected",
                    }
                ),
            )
            self.client.connect(
                self.broker_ip_address, self.broker_port, keepalive=5
            )
            self.client.loop_start()

        except (socket.timeout, ConnectionRefusedError):
            raise BrokerConnectionError

    def tick(self) -> None:
        # This deliberately only deals with one thing at a time
        # Prevents locking up everything else if swamped with messages
        if not self.message_queue.empty():
            self.message_handler(self.message_queue.get())

    def on_connect(
        self, client, userdata, flags, reason_code, properties
    ) -> None:
        if reason_code == 0:
            self.client.publish(
                "/status/discovery",
                json.dumps(
                    {
                        "mac_address": get_mac_address(),
                        "node_name": self.node_name,
                        "status": "connected",
                    }
                ),
            )
            self.mqtt_connected = True
            self.logger.info(
                f"Connected to MQTT broker at {self.broker_ip_address}:{self.broker_port}"
            )
        else:
            raise BrokerConnectionError(reason_code)

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ) -> None:
        self.mqtt_connected = False
        self.logger.warning("Disconnected from MQTT server")

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        # This is called in a seperate thread so put message on queue
        # and let message_handler deal with it
        self.message_queue.put(msg)

    def message_handler(self, msg: mqtt.MQTTMessage) -> None:
        if msg.topic in self.callbacks.keys():
            message = msg.payload.decode("utf-8")
            self.logger.debug(f"Received MQTT: [{msg.topic}] {message}")
            try:
                source_node_id = "Unknown device"
                res = json.loads(message)
                if "node_name" in res.keys():
                    source_node_id = res["node_name"]
                self.callbacks[msg.topic].func(res)

            except UnicodeDecodeError:
                self.logger.warning("Malformed message received")

            except JSONDecodeError:
                self.logger.warning(
                    "Received message contains invalid JSON",
                )
            except KeyError as e:
                self.logger.warning(
                    "Response from device "
                    f"was not complete. Expected key: {e}",
                )
        else:
            self.logger.warning(
                f"Received message on topic: {msg.topic} with no registered callback"
            )

    def publish(self, topic: str, payload: str) -> None:
        if self.mqtt_connected:
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
            self.logger.info(f"Subscribed to MQTT topic: {topic}")

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
            self.logger.info(f"Unsubscribed from MQTT topic: {topic}")

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.client.loop_stop()
        # Don't clean disconnect so LWT gets broadcast
        # self.client.disconnect()
        self.logger.info(
            f"Disconnected from MQTT Server {self.broker_ip_address}:{self.broker_port}",
        )
