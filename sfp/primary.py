# Standard library imports
from typing import Optional
import logging
from enum import Enum, auto

# Third-party library imports
import smbus2

# Local imports
from sfp.common import SFP
from m0wut_drivers.gpio import GPIO


class SFPPrimary(SFP):

    class FSMState(Enum):
        DISCONNECTED = auto()
        QUERYING_SFP = auto()
        INVALID_SFP = auto()
        ACTIVE = auto()
        SFP_TX_FAULT = auto()

    def __init__(
        self,
        i2c_bus: smbus2.SMBus,
        i2c_addr: int,
        gpio_present: GPIO,
        gpio_tx_enable: GPIO,
        gpio_tx_fault: GPIO,
        gpio_los: GPIO,
    ):
        super().__init__(
            i2c_bus=i2c_bus,
            i2c_addr=i2c_addr,
            gpio_present=gpio_present,
            gpio_tx_enable=gpio_tx_enable,
            gpio_tx_fault=gpio_tx_fault,
            gpio_los=gpio_los,
        )

        self.state = self.FSMState.DISCONNECTED
        self.dev.disable_tx()

    def tick(self):
        # Used as a jump table to function corresponding to
        # each state in FSM
        STATE_FUNCTIONS = {
            self.FSMState.DISCONNECTED: self.in_disconnected_state,
            self.FSMState.QUERYING_SFP: self.in_querying_sfp_state,
            self.FSMState.INVALID_SFP: self.in_invalid_sfp_state,
            self.FSMState.ACTIVE: self.in_active_state,
            self.FSMState.SFP_TX_FAULT: self.in_sfp_tx_fault_state,
        }
        STATE_FUNCTIONS[self.state]()

    def in_disconnected_state(self):
        if self.dev.is_present():
            self.logger.debug("SFP Inserted, attempting to read data")
            self.state = self.FSMState.QUERYING_SFP

    def in_querying_sfp_state(self):
        sfp_info = self.dev.read_sfp_info()
        if sfp_info:
            self.logger.info(f"Read SFP info: {sfp_info}")
            self.sfp_info = sfp_info
            self.dev.enable_tx()
            self.state = self.FSMState.ACTIVE
        else:
            self.logger.warning("Failed to read valid SFP Info")  # @TODO
            self.state = self.FSMState.INVALID_SFP

    def in_invalid_sfp_state(self):
        if not self.dev.is_present():
            self.logger.warning("SFP disconnected")  # @TODO
            self.state = self.FSMState.DISCONNECTED

    def in_active_state(self):
        if not self.dev.is_present():
            self.dev.disable_tx()
            self.logger.warning("SFP disconnected")  # @TODO
            self.state = self.FSMState.DISCONNECTED
            return
        if self.dev.tx_fault():
            self.dev.disable_tx()
            self.logger.error("SFP reported TX Fault")  # @TODO
            self.state = self.FSMState.SFP_TX_FAULT

    def in_sfp_tx_fault_state(self):
        if not self.dev.is_present():
            self.logger.info("SFP disconnected")
            self.state = self.FSMState.DISCONNECTED
