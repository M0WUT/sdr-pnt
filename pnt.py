from m0wut_drivers.ds2431 import DS2431
from m0wut_drivers.rs485_message_handler import MessageHandler

from m0wut_drivers.gpio import RPiGPIO, GPIO

from m0wut_drivers.gps_monitor import GPSMonitor, GPSInfo, GPSFixStatus
from m0wut_drivers.git_helper import GitHelper

import config
import time
import logging.config
from typing import Optional
import pathlib
import json


class TimingReference:
    def __init__(
        self,
        logger: logging.Logger,
        is_master: bool = True,
    ):
        self.is_master = is_master
        self.logger = logger
        # LEDs
        self.led_comms_red = RPiGPIO(config.COMMS_RED, GPIO.OUTPUT, GPIO.LOW)
        self.led_comms_green = RPiGPIO(
            config.COMMS_GREEN, GPIO.OUTPUT, GPIO.LOW
        )
        self.led_status_red = RPiGPIO(config.STATUS_RED, GPIO.OUTPUT, GPIO.LOW)
        self.led_status_green = RPiGPIO(
            config.STATUS_GREEN, GPIO.OUTPUT, GPIO.LOW
        )
        # EEPROM
        self.eeprom = DS2431()

        # GPS Monitor
        if self.is_master:
            self.gps_monitor = GPSMonitor()

        # RS485 Traffic Handler
        self.card_address = self.eeprom.read_card_address()
        self.logger.info(f"Read card address as {self.card_address}")
        self.message_handler = MessageHandler(
            config.RS485_UART, 115200, config.RS485_TRX_GPIO, self.card_address
        )

    def wait_for_valid_timesync(self) -> None:
        """
        Blocks until time is synced. If this is a master reference,
        the source is the GPS receiver, is this is an auxiliary reference
        this is a NTP sync with a master reference
        """
        time_synced = False
        while time_synced is False:
            if self.is_master:

                if self.gps_monitor.get_fix_status() in [
                    GPSFixStatus.FIX_2D,
                    GPSFixStatus.FIX_3D,
                ]:
                    time_synced = True
            else:
                # @TODO force NTP sync to master node
                raise NotImplementedError
            self.led_status_red.toggle()
            time.sleep(0.5)


def main(is_master: bool = True):
    git_helper = GitHelper(pathlib.Path())
    # Setup logging
    config_file = pathlib.Path("logging_config.json")
    with open(config_file) as config_in:
        config = json.load(config_in)
    logging.config.dictConfig(config)
    logger = logging.getLogger("reference")
    logger.info(f"Software Version: {git_helper.get_git_version()}")
    reference = TimingReference(logger=logger, is_master=is_master)
    logger.info("Waiting for time synchronisation")
    reference.wait_for_valid_timesync()
    logger.info("Time synchronised. Starting main application!")

    x = 0
    while True:
        reference.led_comms_red.write(x & 0x01)
        reference.led_comms_green.write(x & 0x02)
        reference.led_status_red.write(x & 0x04)
        reference.led_status_green.write(x & 0x08)
        x += 1
        time.sleep(0.1)


if __name__ == "__main__":
    main()
