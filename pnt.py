from m0wut_drivers.ds2431 import DS2431
from m0wut_drivers.rs485_message_handler import MessageHandler

import config


def main():
    eeprom = DS2431()
    card_address = eeprom.read_card_address()
    message_handler = MessageHandler(
        config.RS485_UART, 115200, config.RS485_TRX_GPIO, card_address
    )


if __name__ == "__main__":
    main()
