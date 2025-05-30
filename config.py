# Standard library imports
from pathlib import Path

# Third-party imports
import smbus2

# Local imports
from m0wut_drivers.gpio import GPIO, RPiGPIO, Polarity


# Node Name
NODE_NAME = "Timing Reference - Primary"

# Logging config
LOG_FOLDER_NAME = "log"
LOG_FULL_NAME = "full_log.jsonl"
LOG_WARNING_NAME = "warning_log.jsonl"

# MQTT Config
MQTT_BROKER_IP_ADDRESS = "127.0.0.1"
MQTT_BROKER_PORT = 1883

# RS485 UART
UART_RS485 = Path("/") / "dev" / "ttyAMA5"
GPIO_RS485_TRX = RPiGPIO(23, GPIO.OUTPUT)

# LEDS
GPIO_COMMS_RED = RPiGPIO(9, GPIO.OUTPUT)
GPIO_STATUS_RED = RPiGPIO(10, GPIO.OUTPUT)
GPIO_STATUS_GREEN = RPiGPIO(11, GPIO.OUTPUT)
GPIO_COMMS_GREEN = RPiGPIO(13, GPIO.OUTPUT)

# SFP
I2C_SFP_BUS = smbus2.SMBus(4)
I2C_SFP_ADDRESS = 0x50
GPIO_SFP_PRESENT = RPiGPIO(19, polarity=Polarity.ACTIVE_LOW)
GPIO_SFP_TX_FAULT = RPiGPIO(20)
GPIO_SFP_LOS = RPiGPIO(21)
GPIO_SFP_TX_ENABLE = RPiGPIO(26, GPIO.OUTPUT)


# Reference Clok
REF_CLK_SELECT = RPiGPIO(12, GPIO.OUTPUT)
