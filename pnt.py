# Local imports
import logging.handlers
import time
import logging.config
from typing import Optional
import pathlib
import json
import atexit

# Third-party imports
import smbus2

# Local imports
from m0wut_drivers.ds2431 import DS2431
from m0wut_drivers.rs485_message_handler import MessageHandler
from m0wut_drivers.gpio import RPiGPIO, GPIO
from m0wut_drivers.gps_monitor import GPSMonitor, GPSInfo, GPSFixStatus
from m0wut_drivers.git_helper import GitHelper
import config
from sfp.primary import SFPPrimary
from mqtt.mqtt_handler import MqttHandler
from warning_handler.warning_handler import WarningHandler


class TimingReference:
    def __init__(
        self,
        logger: logging.Logger,
        is_master: bool = True,
    ):
        self.logger = logger
        # EEPROM
        self.eeprom = DS2431()

        # GPS Monitor
        if is_master:
            self.gps_monitor = GPSMonitor()
        else:
            self.gps_monitor = None

        # RS485 Traffic Handler
        self.card_address = self.eeprom.read_card_address()
        self.logger.info(f"Read card address as {self.card_address}")
        self.message_handler = MessageHandler(
            config.UART_RS485, 115200, config.GPIO_RS485_TRX, self.card_address
        )

    def wait_for_valid_timesync(self) -> None:
        """
        Blocks until time is synced. If this is a master reference,
        the source is the GPS receiver, is this is an auxiliary reference
        this is a NTP sync with a master reference
        """

        if self.gps_monitor:
            while self.gps_monitor.get_fix_status() not in [
                GPSFixStatus.FIX_2D,
                GPSFixStatus.FIX_3D,
            ]:
                # self.led_status_red.toggle()
                time.sleep(0.5)
        else:
            # @TODO NTP sync to master node
            raise NotImplementedError


def main(is_master: bool = True):
    pass
    git_helper = GitHelper(pathlib.Path())

    # Setup logging
    config_file = pathlib.Path("logging_config.json")
    with open(config_file) as config_in:
        logging.config.dictConfig(json.load(config_in))
    logger = logging.getLogger(__name__)
    logger.info(f"Software Version: {git_helper.get_git_version()}")

    # There's a nice function "getHandlerByName" but it's Python 3.12 only :(
    warning_handler = [
        x for x in logging.getLogger().handlers if isinstance(x, WarningHandler)
    ][0]
    mqtt = warning_handler.mqtt

    with SFPPrimary(
        i2c_bus=config.I2C_SFP_BUS,
        i2c_addr=config.I2C_SFP_ADDRESS,
        gpio_present=config.GPIO_SFP_PRESENT,
        gpio_tx_enable=config.GPIO_SFP_TX_ENABLE,
        gpio_tx_fault=config.GPIO_SFP_TX_FAULT,
        gpio_los=config.GPIO_SFP_LOS,
    ) as sfp:
        while True:
            sfp.tick()
            warning_handler.tick()
            time.sleep(0.1)

    # # Wait for time synchronisation
    # reference = TimingReference(logger=logger, is_master=is_master)
    # logger.info("Waiting for time synchronisation")
    # reference.wait_for_valid_timesync()
    # logger.info("Time synchronised. Starting main application!")
    # reference.led_status_red.write(0)
    # reference.led_status_green.write(1)

    # # Here we go!

    # x = 0
    # while True:
    #     # reference.led_comms_red.write(x & 0x01)
    #     # reference.led_comms_green.write(x & 0x02)
    #     # reference.led_status_red.write(x & 0x04)
    #     # reference.led_status_green.write(x & 0x08)
    #     x += 1
    #     time.sleep(0.5)


if __name__ == "__main__":
    main()
