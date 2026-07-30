import time
from pyb import UART, LED

uart = UART(1, 9600)   # P1=TX, P0=RX
led = LED(3)

for _ in range(3):
    led.on()
    time.sleep_ms(200)
    led.off()
    time.sleep_ms(200)
led.on()

while True:
    if uart.any():
        b = uart.read(1)[0]
        if b == 0x01:
            led.off()
            time.sleep_ms(100)
            led.on()
            uart.write(b'\x02')
    time.sleep_ms(10)
