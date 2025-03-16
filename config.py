# Standard library imports
from pathlib import Path

# Third-party imports
import smbus2

# Local imports
from m0wut_drivers.gpio import GPIO, RPiGPIO

# RS485 UART
UART_RS485 = Path("/") / "dev" / "ttyAMA5"
GPIO_RS485_TRX = RPiGPIO(23, GPIO.OUTPUT)

# # LEDS
GPIO_COMMS_RED = 9
GPIO_STATUS_RED = 10
GPIO_STATUS_GREEN = 11
GPIO_COMMS_GREEN = 13

# SFP
I2C_SFP_BUS = smbus2.SMBus(4)
I2C_SFP_ADDRESS = 0x50
GPIO_SFP_PRESETN = RPiGPIO(19)
GPIO_SFP_TX_FAULT = RPiGPIO(20)
GPIO_SFP_LOS = RPiGPIO(21)
GPIO_SFP_TX_ENABLE = RPiGPIO(26, GPIO.OUTPUT)
