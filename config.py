from pathlib import Path
from m0wut_drivers.gpio import GPIO, RPiGPIO


RS485_UART = Path("/dev") / "ttyAMA0"
RS485_TRX_GPIO = RPiGPIO(7, GPIO.OUTPUT)
