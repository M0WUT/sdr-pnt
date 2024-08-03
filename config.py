from pathlib import Path
from m0wut_drivers.gpio import GPIO, RPiGPIO

# RS485 UART
RS485_UART = Path("/dev") / "ttyAMA0"
RS485_TRX_GPIO = RPiGPIO(7, GPIO.OUTPUT)

# LEDS
COMMS_RED = 9
STATUS_RED = 10
STATUS_GREEN = 11
COMMS_GREEN = 13
