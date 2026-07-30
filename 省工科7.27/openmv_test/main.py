# main.py — 手动测试版（通过 IDE 串口终端发命令，不依赖 STM32）
#
# IDE 串口终端发送格式：
#   1        → QR 扫描
#   2r       → 红色排爆物   (r=红 g=绿 b=蓝)
#   2g       → 绿色排爆物
#   2b       → 蓝色排爆物
#   3r       → 红色靶标
#   3g       → 绿色靶标
#   3b       → 蓝色靶标
#   4c       → 圆柱人质   (c=圆柱 t=圆锥 d=腰鼓)
#   4t       → 圆锥人质
#   4d       → 腰鼓人质
#   5        → 排爆桶
#   s        → 停止当前模式，回到空闲

import sensor
import image
import time
from pyb import UART
from pyb import LED

uart = UART(3, 115200)  # P4(TX) P5(RX)，连 STM32
led = LED(3)

# ==================== USB 串口（IDE 终端）====================
import pyb
usb = pyb.USB_VCP()


def usb_read_cmd():
    """从 IDE 串口终端读取命令，返回 (cmd, param) 或 (None, None)"""
    if usb.any():
        line = usb.readline().decode().strip()
        if not line:
            return (None, None)

        if line == "s":
            return (0xFF, None)

        if len(line) == 1:
            if line == "1":
                return (0x01, None)
            elif line == "5":
                return (0x05, None)

        if len(line) == 2:
            cmd_char = line[0]
            param_char = line[1]
            color_map = {"r": 1, "g": 2, "b": 3}
            shape_map = {"c": 1, "t": 2, "d": 3}

            if cmd_char == "2" and param_char in color_map:
                return (0x02, color_map[param_char])
            elif cmd_char == "3" and param_char in color_map:
                return (0x03, color_map[param_char])
            elif cmd_char == "4" and param_char in shape_map:
                return (0x04, shape_map[param_char])

    return (None, None)


# ==================== 命令字 ====================
CMD_QR     = 0x01
CMD_BOMB   = 0x02
CMD_TARGET = 0x03
CMD_RESCUE = 0x04
CMD_BIN    = 0x05
CMD_STOP   = 0xFF


def _blink():
    led.off()
    time.sleep_ms(150)
    led.on()
    time.sleep_ms(150)
    led.off()


# ==================== 模式函数 ====================

def mode_qr():
    from QRcode import reset_module, _init_sensor, scan_qr_frame
    reset_module()
    _init_sensor()
    print("[QR] 开始扫描...")

    while True:
        cmd, _ = usb_read_cmd()
        if cmd and cmd != CMD_QR:
            return (cmd, None)

        result = scan_qr_frame()
        if result:
            d1, d2, d3 = result
            buf = bytes([0xA3, 0xB3, CMD_QR, d1, d2, d3, 0xC3])
            uart.write(buf)
            print("[QR] 识别到: %d%d%d  已发送: %s" % (d1, d2, d3, buf.hex()))
            return (0, None)

        time.sleep_ms(30)


def mode_bomb(color):
    from bomb import reset_module, _init_sensor, detect_bomb
    names = {1: "红", 2: "绿", 3: "蓝"}
    reset_module()
    _init_sensor()
    print("[排爆] 查找%s色爆炸物..." % names.get(color, "?"))

    last_send = time.ticks_ms()
    while True:
        cmd, param = usb_read_cmd()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_bomb(color)
            if result:
                X, Y, Dist = result
            else:
                X, Y, Dist = 0, 0, 0
            buf = bytes([0xA3, 0xB3, CMD_BOMB, X, Y, Dist, 0xC3])
            uart.write(buf)
            print("[排爆] X=%3d Y=%3d Dist=%2d cm" % (X, Y, Dist))
            last_send = now


def mode_bin():
    from bomb import reset_module, _init_sensor, detect_bin
    reset_module()
    _init_sensor()
    print("[排爆桶] 查找中...")

    last_send = time.ticks_ms()
    while True:
        cmd, param = usb_read_cmd()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_bin()
            if result:
                binX, binY = result
            else:
                binX, binY = 0, 0
            buf = bytes([0xA3, 0xB3, CMD_BIN, binX, binY, 0xC3])
            uart.write(buf)
            print("[排爆桶] X=%3d Y=%3d" % (binX, binY))
            last_send = now


def mode_target(color):
    from target import reset_module, _init_sensor, detect_target
    names = {1: "红", 2: "绿", 3: "蓝"}
    reset_module()
    _init_sensor()
    print("[靶标] 查找%s色靶标..." % names.get(color, "?"))

    last_send = time.ticks_ms()
    while True:
        cmd, param = usb_read_cmd()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_target(color)
            if result:
                tX, tY, Dist = result
            else:
                tX, tY, Dist = 0, 0, 0
            buf = bytes([0xA3, 0xB3, CMD_TARGET, tX, tY, Dist, 0xC3])
            uart.write(buf)
            print("[靶标] X=%3d Y=%3d Dist=%2d cm" % (tX, tY, Dist))
            last_send = now


def mode_rescue(shape):
    from rescue import reset_module, _init_sensor, detect_rescue
    names = {1: "圆柱", 2: "圆锥", 3: "腰鼓"}
    reset_module()
    _init_sensor()
    print("[救援] 查找%s人质..." % names.get(shape, "?"))

    last_send = time.ticks_ms()
    while True:
        cmd, param = usb_read_cmd()
        if cmd:
            return (cmd, param)

        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= 100:
            result = detect_rescue(shape)
            if result:
                sX, sY, H = result
            else:
                sX, sY, H = 0, 0, 0
            buf = bytes([0xA3, 0xB3, CMD_RESCUE, sX, sY, H, 0xC3])
            uart.write(buf)
            print("[救援] X=%3d Y=%3d H=%3d px" % (sX, sY, H))
            last_send = now


# ==================== 主调度 ====================
current_cmd = 0
current_param = None

for _ in range(3):
    led.on()
    time.sleep_ms(200)
    led.off()
    time.sleep_ms(200)

print("\n===== 排爆机器人 OpenMV 测试版 =====")
print("  1      = QR 扫描")
print("  2r/g/b = 排爆物 (红/绿/蓝)")
print("  3r/g/b = 靶标   (红/绿/蓝)")
print("  4c/t/d = 人质   (圆柱/圆锥/腰鼓)")
print("  5      = 排爆桶")
print("  s      = 停止\n")

while True:
    cmd, param = usb_read_cmd()
    if cmd:
        if cmd == CMD_STOP:
            print("[停止] 回空闲")
            current_cmd = 0
            current_param = None
        else:
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
        time.sleep_ms(10)
