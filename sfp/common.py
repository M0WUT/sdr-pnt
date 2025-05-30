# Standard library imports
from typing import Optional
import logging

# Third-party library imports
import smbus2

# Local imports
from m0wut_drivers.sfp import SFP as SFPDev
from m0wut_drivers.gpio import GPIO


class SFP:
    def __init__(
        self,
        i2c_bus: smbus2.SMBus,
        i2c_addr: int,
        gpio_present: Optional[GPIO] = None,
        gpio_tx_enable: Optional[GPIO] = None,
        gpio_tx_fault: Optional[GPIO] = None,
        gpio_los: Optional[GPIO] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.dev = SFPDev(
            i2c_bus=i2c_bus,
            i2c_addr=i2c_addr,
            gpio_present=gpio_present,
            gpio_tx_enable=gpio_tx_enable,
            gpio_tx_fault=gpio_tx_fault,
            gpio_los=gpio_los,
        )
        self.logger = logger if logger else logging.getLogger(__name__)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.dev.__exit__()

    def tick(self):
        # Function that should be called periodically to keep the
        # state machine going
        raise NotImplementedError
