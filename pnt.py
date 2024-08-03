from m0wut_drivers.ds2431 import DS2431
from m0wut_drivers.rs485_message_handler import MessageHandler

from m0wut_drivers.gpio import RPiGPIO, GPIO

import config


def main():
    led_comms_red = RPiGPIO(config.COMMS_RED, GPIO.OUTPUT, GPIO.LOW)
    led_comms_green = RPiGPIO(config.COMMS_GREEN, GPIO.OUTPUT, GPIO.LOW)
    led_status_red = RPiGPIO(config.STATUS_RED, GPIO.OUTPUT, GPIO.LOW)
    led_status_green = RPiGPIO(config.STATUS_GREEN, GPIO.OUTPUT, GPIO.LOW)
    eeprom = DS2431()
    card_address = eeprom.read_card_address()
    message_handler = MessageHandler(
        config.RS485_UART, 115200, config.RS485_TRX_GPIO, card_address
    )

    import time

    x = 0

    while True:
        led_comms_red.write(x & 0x01)
        led_comms_green.write(x & 0x02)
        led_status_red.write(x & 0x04)
        led_status_green.write(x & 0x08)
        x += 1
        time.sleep(0.1)


if __name__ == "__main__":
    main()
