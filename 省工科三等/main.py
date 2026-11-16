# main.py — OpenMV 上电自动运行
# 状态机架构：每种任务是一个模式，模式内持续上报，
# 全部模式均由 STM32 发命令切换

from pyb import UART, LED
import time
from pyb import Pin
uart = UART(3, 115200)  # P4(TX) P5(RX)

# 补光灯 — 常亮，接 P6，改引脚改这里
light = Pin('P6', Pin.OUT_PP)
light.high()

# ==================== 命令字 ====================
CMD_QR = 0x01  # 二维码扫描（无参数，自动确认后退出）
CMD_BOMB = 0x02  # 排爆物定位（参数：1=红 2=绿 3=蓝）
CMD_TARGET = 0x03  # 靶标定位    （参数：1=红 2=绿 3=蓝）
CMD_RESCUE = 0x04  # 人质识别    （参数：1=圆柱 2=圆锥 3=腰鼓）
CMD_BIN = 0x05  # 排爆桶定位  （无参数）
CMD_LINE = 0x06  # 巡线         （无参数）

# ==================== 帧格式 ====================
# QR:     A3 B3 01 d1 d2 d3 C3          (7 字节)
# BOMB:   A3 B3 02 X Y flag C3          (7 字节, flag=1 到达夹取点)
# TARGET: A3 B3 03 tX tY flag C3        (7 字节, flag=1 到达夹取点)
# RESCUE: A3 B3 04 sX sY flag C3        (7 字节, flag=1 到达夹取点)
# BIN:    A3 B3 05 binX binY flag C3     (7 字节, flag=1 到达投放点)
# LINE:   A3 B3 06 X 00 flag C3         (7 字节, X=赛道中心, flag=1 本帧有效)


def read_command():
    """非阻塞读取命令，返回 (cmd, param) 或 (None, None)"""
    if uart.any():
        b = uart.readchar()
        if b == CMD_QR or b == CMD_BIN or b == CMD_LINE:
            return (b, None)
        elif b in (CMD_BOMB, CMD_TARGET, CMD_RESCUE):
            deadline = time.ticks_ms() + 50
            while time.ticks_ms() < deadline:
                if uart.any():
                    param = uart.readchar()
                    return (b, param)
            return (None, None)
    return (None, None)


# ==================== 各模式函数 ====================

def mode_qr():
    from QRcode import reset_module, _init_sensor, scan_qr_frame

    reset_module()
    _init_sensor()

    while True:
        cmd, param = read_command()
        if cmd and cmd != CMD_QR:
            print("[MODE] qr exit cmd=0x%02X param=%r" % (cmd, param))
            return (cmd, param)

        result = scan_qr_frame()
        if result:
            d1, d2, d3 = result
            uart.write(bytes([0xA3, 0xB3, CMD_QR, d1, d2, d3, 0xC3]))
        else:
            uart.write(bytes([0xA3, 0xB3, CMD_QR, 0, 0, 0, 0xC3]))


def mode_bomb(color):
    print("[MODE] bomb color=%r" % (color,))
    from bomb import reset_module, detect_bomb

    reset_module()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        result = detect_bomb(color)
        if result:
            X, Y, flag = result
        else:
            X, Y, flag = 0, 0, 0
        uart.write(bytes([0xA3, 0xB3, CMD_BOMB, X, Y, flag, 0xC3]))


def mode_bin():
    from bomb import reset_module, detect_bin

    reset_module()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        result = detect_bin()
        if result:
            binX, binY, flag = result
        else:
            binX, binY, flag = 0, 0, 0
        uart.write(bytes([0xA3, 0xB3, CMD_BIN, binX, binY, flag, 0xC3]))


def mode_target(color):
    print("[MODE] target color=%r" % (color,))
    from target import reset_module, _init_sensor, detect_target

    reset_module()
    _init_sensor()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        result = detect_target(color)
        if result:
            tX, tY, flag = result
        else:
            tX, tY, flag = 0, 0, 0
        uart.write(bytes([0xA3, 0xB3, CMD_TARGET, tX, tY, flag, 0xC3]))


def mode_rescue(shape):
    print("[MODE] rescue shape=%r" % (shape,))
    from rescue import reset_module, _init_sensor, detect_rescue

    reset_module()
    _init_sensor()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        result = detect_rescue(shape)
        if result:
            sX, sY, flag = result
        else:
            sX, sY, flag = 0, 0, 0
        uart.write(bytes([0xA3, 0xB3, CMD_RESCUE, sX, sY, flag, 0xC3]))


def mode_line():
    from line import reset_module, detect_line

    reset_module()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        X, flag = detect_line()
        uart.write(bytes([0xA3, 0xB3, CMD_LINE, X, 0, flag, 0xC3]))


# ==================== 主调度 ====================
current_cmd = 0
current_param = None

led = LED(3)


def _blink():
    """任务切换时快闪一次"""
    led.off()
    time.sleep_ms(150)
    led.on()
    time.sleep_ms(150)
    led.off()


# 上电后交替闪烁 3 次，表示已就绪
for _ in range(3):
    led.on()
    time.sleep_ms(200)
    led.off()
    time.sleep_ms(200)

while True:
    cmd, param = read_command()
    if cmd:
        current_cmd = cmd
        current_param = param

    if current_cmd == CMD_QR:
        led.on()
        next_cmd, next_param = mode_qr()
        _blink()
        current_cmd = next_cmd
        current_param = next_param

    elif current_cmd == CMD_BOMB:
        led.on()
        next_cmd, next_param = mode_bomb(current_param)
        _blink()
        current_cmd = next_cmd
        current_param = next_param

    elif current_cmd == CMD_BIN:
        led.on()
        next_cmd, next_param = mode_bin()
        _blink()
        current_cmd = next_cmd
        current_param = next_param

    elif current_cmd == CMD_TARGET:
        led.on()
        next_cmd, next_param = mode_target(current_param)
        _blink()
        current_cmd = next_cmd
        current_param = next_param

    elif current_cmd == CMD_RESCUE:
        led.on()
        next_cmd, next_param = mode_rescue(current_param)
        _blink()
        current_cmd = next_cmd
        current_param = next_param

    elif current_cmd == CMD_LINE:
        led.on()
        next_cmd, next_param = mode_line()
        _blink()
        current_cmd = next_cmd
        current_param = next_param

    else:
        # 空闲状态，LED 灭
        time.sleep_ms(10)
