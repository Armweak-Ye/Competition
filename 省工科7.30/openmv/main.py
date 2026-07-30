# main.py — OpenMV 上电自动运行
# 状态机架构：每种任务是一个模式，模式内持续上报，
# QR 模式自动确认退出，其他模式由 STM32 发命令切换

from pyb import UART, LED
import time

uart = UART(3, 115200)  # P4(TX) P5(RX)

# 补光灯 — 常亮，接 P6，改引脚改这里
from pyb import Pin
light = Pin('P6', Pin.OUT_PP)
light.high()

# ==================== 命令字 ====================
CMD_QR     = 0x01  # 二维码扫描（无参数，自动确认后退出）
CMD_BOMB   = 0x02  # 排爆物定位（参数：1=红 2=绿 3=蓝）
CMD_TARGET = 0x03  # 靶标定位    （参数：1=红 2=绿 3=蓝）
CMD_RESCUE = 0x04  # 人质识别    （参数：1=圆柱 2=圆锥 3=腰鼓）
CMD_BIN    = 0x05  # 排爆桶定位  （无参数）

# ==================== 帧格式 ====================
# QR:     A3 B3 01 d1 d2 d3 C3          (7 字节)
# BOMB:   A3 B3 02 X Y Dist C3          (7 字节)
# TARGET: A3 B3 03 tX tY Dist C3        (7 字节)
# RESCUE: A3 B3 04 sX sY Dist flag C3   (8 字节, flag=1 表示模板确认)
# BIN:    A3 B3 05 binX binY C3         (6 字节)


def read_command():
    """非阻塞读取命令，返回 (cmd, param) 或 (None, None)"""
    if uart.any():
        b = uart.readchar()
        if b == CMD_QR or b == CMD_BIN:
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
    """
    QR 扫描模式。
    连续读码，读到一次合法结果即上报并退出。
    """
    from QRcode import reset_module, _init_sensor, scan_qr_frame

    reset_module()
    _init_sensor()

    while True:
        cmd, _ = read_command()
        if cmd and cmd != CMD_QR:
            return (cmd, None)

        result = scan_qr_frame()
        if result:
            d1, d2, d3 = result
            uart.write(bytes([0xA3, 0xB3, CMD_QR, d1, d2, d3, 0xC3]))
            return (0, None)

        time.sleep_ms(30)


def mode_bomb(color):
    """
    排爆物持续定位模式。
    每 ~100ms 上报一次 (X, Y, Dist)，直到 STM32 发新命令。
    """
    from bomb import reset_module, _init_sensor, detect_bomb

    reset_module()
    _init_sensor()

    last_send = time.ticks_ms()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_bomb(color)
            if result:
                X, Y, Dist = result
            else:
                X, Y, Dist = 0, 0, 0
            uart.write(bytes([0xA3, 0xB3, CMD_BOMB, X, Y, Dist, 0xC3]))
            last_send = now


def mode_bin():
    """
    排爆桶持续定位模式。
    每 ~100ms 上报一次 (binX, binY)，直到 STM32 发新命令。
    """
    from bomb import reset_module, _init_sensor, detect_bin

    reset_module()
    _init_sensor()

    last_send = time.ticks_ms()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_bin()
            if result:
                binX, binY = result
            else:
                binX, binY = 0, 0
            uart.write(bytes([0xA3, 0xB3, CMD_BIN, binX, binY, 0xC3]))
            last_send = now


def mode_target(color):
    """
    靶标持续定位模式。
    每 ~100ms 上报一次 (tX, tY, Dist)，直到 STM32 发新命令。
    """
    from target import reset_module, _init_sensor, detect_target

    reset_module()
    _init_sensor()

    last_send = time.ticks_ms()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_target(color)
            if result:
                tX, tY, Dist = result
            else:
                tX, tY, Dist = 0, 0, 0
            uart.write(bytes([0xA3, 0xB3, CMD_TARGET, tX, tY, Dist, 0xC3]))
            last_send = now


def mode_rescue(shape):
    """
    人质持续识别模式。
    每 ~100ms 上报一次 (sX, sY, Dist, flag)，直到 STM32 发新命令。
    flag=1 表示模板匹配确认了形状。
    """
    from rescue import reset_module, _init_sensor, detect_rescue

    reset_module()
    _init_sensor()

    last_send = time.ticks_ms()

    while True:
        cmd, param = read_command()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_rescue(shape)
            if result:
                sX, sY, Dist, flag = result
            else:
                sX, sY, Dist, flag = 0, 0, 0, 0
            uart.write(bytes([0xA3, 0xB3, CMD_RESCUE,
                              sX, sY, Dist, flag, 0xC3]))
            last_send = now


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

    else:
        # 空闲状态，LED 灭
        time.sleep_ms(10)
