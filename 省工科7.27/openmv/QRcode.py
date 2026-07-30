# QRcode.py — 二维码扫描模块
# 由 main.py 调用

import sensor
import image

_sensor_ready = False

def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False

def _init_sensor():
    global _sensor_ready
    if _sensor_ready:
        return
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)     # 二维码不需要颜色
    sensor.set_framesize(sensor.VGA)
    sensor.skip_frames(70)
    _sensor_ready = True


def scan_qr_frame():
    """
    单帧扫描二维码。
    返回 (d1, d2, d3) 或 None。
    """
    img = sensor.snapshot()

    codes = img.find_qrcodes()
    if codes:
        payload = codes[0].payload()
        if len(payload) == 3 and payload.isdigit():
            d1 = int(payload[0])
            d2 = int(payload[1])
            d3 = int(payload[2])
            if 1 <= d1 <= 3 and 1 <= d2 <= 3 and 1 <= d3 <= 3:
                return (d1, d2, d3)
    return None
