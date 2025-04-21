# Standard imports
from typing import Callable, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import json
from logging import Handler, LogRecord, ERROR, WARNING
from queue import Queue
import logging
from time import sleep
from pathlib import Path

# Third-party imports


# Local imports
from m0wut_drivers.gpio import GPIO
from m0wut_drivers.linux_cpu import get_mac_address
from config import (
    GPIO_STATUS_GREEN,
    GPIO_STATUS_RED,
    MQTT_BROKER_IP_ADDRESS,
    MQTT_BROKER_PORT,
    NODE_NAME,
    LOG_FOLDER_NAME,
    LOG_FULL_NAME,
    LOG_WARNING_NAME,
)
from mqtt.mqtt_handler import MqttHandler, BrokerConnectionError
from paho.mqtt.client import MQTTMessage


class Notification:
    def __init__(
        self,
        mac_address: str,
        node_name: str,
        category: str,
        message: str,
        full_log_file: Path,
        warning_log_file: Path,
    ):
        self.mac_address = mac_address
        self.node_name = node_name
        self.category = category
        self.message = message
        self.creation_time: datetime = datetime.now(tz=timezone.utc)
        self.datetime_strf_string: str = "%Y-%m-%dT%H:%M:%S%z"
        if isinstance(self, (Warning, Error)):
            with open(warning_log_file, "a+") as file:
                file.write(str(self) + "\n")

        with open(full_log_file, "a+") as file:
            file.write(str(self) + "\n")

    def __str__(self) -> str:
        return json.dumps(
            {
                "mac_address": self.mac_address,
                "node_name": self.node_name,
                "category": self.category,
                "message": self.message,
                "time": self.creation_time.isoformat(timespec="milliseconds"),
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
        self.mac_address = get_mac_address()
        self.warnings: list[Warning] = []
        self.errors: list[Error] = []
        self.green_led = green_led
        self.red_led = red_led
        self.last_blink_time: datetime = datetime.now()
        self.blink_period_s = blink_period_s
        self.led_state: bool = False
        self.mqtt: Optional[MqttHandler] = None
        self.logger: Optional[logging.Logger] = None
        self.initialised: bool = False

    def initialise(self):
        """
        Because this handler is automatically initialised when the logging handlers are setup,
        it gets a bit messy as you have things making errors before the logging handler is initialised.
        As such, the initialise that might create errors of its own e.g. connecting to MQTT server
        need to be done separately. This should be called the first time self.tick() is called
        """
        # Setup logger
        self.logger = logging.getLogger(__name__)

        # Try to save logs on SSD to save wear on eMMC but it might not be there
        ssd_path = Path("/") / "mnt" / "media" / "nvme"
        if ssd_path.exists():
            log_folder = ssd_path / LOG_FOLDER_NAME
        else:
            log_folder = Path(LOG_FOLDER_NAME)

        # Make files / folders
        log_folder.parent.mkdir(parents=True, exist_ok=True)
        self.warning_log = log_folder / LOG_WARNING_NAME
        self.full_log = log_folder / LOG_FULL_NAME

        while self.mqtt is None:
            try:
                self.mqtt = MqttHandler(
                    MQTT_BROKER_IP_ADDRESS, MQTT_BROKER_PORT, NODE_NAME
                )
                self.logger.debug("Waiting to connect to MQTT broker")
                while not self.mqtt.mqtt_connected:
                    sleep(0.1)
            except BrokerConnectionError:
                self.red_led.write(1)
                self.logger.error(
                    f"Failed to connect to broker at {MQTT_BROKER_IP_ADDRESS}:{MQTT_BROKER_PORT}",
                )
                sleep(5)
        self._clear_errors()
        self.red_led.write(0)

        # Setup callback functions
        self.mqtt.register_callback("/status/warnings", self.rx_warnings)
        self.mqtt.register_callback("/status/errors", self.rx_errors)

        self.initialised = True

    def emit(self, record: LogRecord):
        """
        This must be called "emit". This is the handler called automatically
        by the logging config any time any module uses the root logger
        """
        if record.levelno >= ERROR:
            self.add_error(
                self.mac_address,
                self.node_name,
                record.name,
                record.getMessage(),
            )
        elif record.levelno == WARNING:
            self.add_warning(
                self.mac_address,
                self.node_name,
                record.name,
                record.getMessage(),
            )
        else:
            self.add_info(
                self.mac_address,
                self.node_name,
                record.name,
                record.getMessage(),
            )

    def add_error(
        self,
        mac_address: str,
        node_name: str,
        category: str,
        message: str,
        broadcast: bool = True,
    ):
        x = Error(
            mac_address,
            node_name,
            category,
            message,
            self.full_log,
            self.warning_log,
        )
        self.errors.append(x)
        if broadcast and self.mqtt is not None:
            self.mqtt.publish("/status/errors", str(x))

    def add_warning(
        self,
        mac_address: str,
        node_name: str,
        category: str,
        message: str,
        broadcast: bool = True,
    ):
        x = Warning(
            mac_address,
            node_name,
            category,
            message,
            self.full_log,
            self.warning_log,
        )
        self.warnings.append(x)
        if broadcast and self.mqtt is not None:
            self.mqtt.publish("/status/warnings", str(x))

    def add_info(
        self,
        mac_address: str,
        node_name: str,
        category: str,
        message: str,
        broadcast: bool = True,
    ):
        if broadcast and self.mqtt is not None:
            # Don't bother storing info in running code - just useful for debug / logging
            x = Info(
                mac_address,
                node_name,
                category,
                message,
                self.full_log,
                self.warning_log,
            )
            self.mqtt.publish("/status/info", str(x))

    def _clear_warnings(self):
        self.warnings = []

    def _clear_errors(self):
        self.errors = []

    def _has_warnings(self) -> bool:
        """
        As the primary timing reference is also the MQTT broker, it shall store warnings / errors
        generated by all nodes, not just itself.
        Returns True if this node has errors
        """
        current_node_warnings = [
            x for x in self.warnings if x.node_name == self.node_name
        ]
        return bool(len(current_node_warnings) > 0)

    def _has_errors(self) -> bool:
        """
        Returns True if this node has errors
        """
        current_node_errors = [
            x for x in self.errors if x.node_name == self.node_name
        ]
        return bool(len(current_node_errors) > 0)

    def rx_warnings(self, message_dict: dict[str, str]) -> None:
        """
        Handles the logging of warnings received from other nodes
        """
        self.add_warning(
            mac_address=message_dict["mac_address"],
            node_name=message_dict["node_name"],
            category=message_dict["category"],
            message=message_dict["message"],
            broadcast=False,
        )

    def rx_errors(self, message_dict: dict[str, str]) -> None:
        """
        Handles the logging of errors received from other nodes
        """
        self.add_error(
            mac_address=message_dict["mac_address"],
            node_name=message_dict["node_name"],
            category=message_dict["category"],
            message=message_dict["message"],
            broadcast=False,
        )

    def tick(self):
        if not self.initialised:
            self.initialise()
        x = datetime.now()
        if (
            x - self.last_blink_time
        ).total_seconds() > 0.5 * self.blink_period_s:
            # Toggle virtual LED
            self.led_state = not self.led_state
            self.last_blink_time = x
            # LED configuration is a combined Red / Green (i.e. can be combined to make orange)
            if self._has_errors() or not self.mqtt.mqtt_connected:
                # Blink red
                self.green_led.write(0)
                self.red_led.write(self.led_state)
            elif self._has_warnings():
                # Blink orange
                self.green_led.write(self.led_state)
                self.red_led.write(self.led_state)
            else:
                # Everything working :) - solid green
                self.green_led.write(1)
                self.red_led.write(0)
