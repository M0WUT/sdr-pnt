# Standard imports
from typing import Callable, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import json
from logging import Handler, LogRecord, ERROR, WARNING
from queue import Queue
import logging
from time import sleep

# Third-party imports


# Local imports
from m0wut_drivers.gpio import GPIO
from config import (
    GPIO_STATUS_GREEN,
    GPIO_STATUS_RED,
    MQTT_BROKER_IP_ADDRESS,
    MQTT_BROKER_PORT,
    NODE_NAME,
)
from mqtt.mqtt_handler import MqttHandler, BrokerConnectionError


@dataclass(frozen=True)
class Notification:
    node_name: str
    category: str
    message: str
    creation_time: datetime = datetime.now(tz=timezone.utc)
    datetime_strf_string: str = "%Y-%m-%dT%H:%M:%S%z"

    def __str__(self) -> str:
        return json.dumps(
            {
                "name": self.node_name,
                "category": self.category,
                "message": self.message,
                "time": self.creation_time.strftime(self.datetime_strf_string),
            }
        )


class Info(Notification):
    pass


class Warning(Notification):
    pass


class Error(Notification):
    pass


class WarningHandler(Handler):
    def __init__(
        self,
        green_led: GPIO = GPIO_STATUS_GREEN,
        red_led: GPIO = GPIO_STATUS_RED,
        blink_period_s: float = 1,
    ):
        super().__init__()
        self.node_name = NODE_NAME
        self.warnings: list[Warning] = []
        self.errors: list[Error] = []
        self.green_led = green_led
        self.red_led = red_led
        self.last_blink_time: datetime = datetime.now()
        self.blink_period_s = blink_period_s
        self.led_state: bool = False
        self.mqtt = None
        self.logger = logging.getLogger(__name__)
        while self.mqtt is None:
            try:
                self.mqtt = MqttHandler(
                    MQTT_BROKER_IP_ADDRESS, MQTT_BROKER_PORT, NODE_NAME
                )
            except BrokerConnectionError:
                self.red_led.write(1)
                self.logger.error(
                    f"Failed to connect to broker at {MQTT_BROKER_IP_ADDRESS}:{MQTT_BROKER_PORT}",
                )
                sleep(5)
        self.red_led.write(0)

    def add_info(
        self,
        node_name: str,
        category: str,
        message: str,
        broadcast: bool = True,
    ):
        x = Info(node_name, category, message)
        # Don't bother logging info - just useful for debug
        if broadcast and self.mqtt is not None:
            self.mqtt.publish("/discovery/info", str(x))

    def emit(self, record: LogRecord):
        if record.levelno >= ERROR:
            self.add_error(self.node_name, record.name, record.getMessage())
        elif record.levelno == WARNING:
            self.add_error(self.node_name, record.name, record.getMessage())
        else:
            self.add_info(self.node_name, record.name, record.getMessage())

    def add_warning(
        self,
        node_name: str,
        category: str,
        message: str,
        broadcast: bool = True,
    ):
        x = Warning(node_name, category, message)
        self.warnings.append(x)
        if broadcast and self.mqtt is not None:
            self.mqtt.publish("/discovery/warnings", str(x))

    def add_error(
        self,
        node_name: str,
        category: str,
        message: str,
        broadcast: bool = True,
    ):
        x = Error(node_name, category, message)
        self.errors.append(x)
        if broadcast and self.mqtt is not None:
            self.mqtt.publish("/discovery/errors", str(x))

    def _clear_warnings(self):
        self.warnings = []

    def _clear_errors(self):
        self.errors = []

    def tick(self):
        x = datetime.now()
        if (
            x - self.last_blink_time
        ).total_seconds() > 0.5 * self.blink_period_s:
            # Toggle virtual LED
            self.led_state = not self.led_state
            self.last_blink_time = x
            # LED configuration is a combined Red / Green (i.e. can be combined to make orange)
            if self.errors:
                # Blink red
                self.green_led.write(0)
                self.red_led.write(self.led_state)
            elif self.warnings:
                # Blink orange
                self.green_led.write(self.led_state)
                self.red_led.write(self.led_state)
            else:
                # Everything working :) - solid green
                self.green_led.write(1)
                self.red_led.write(0)
