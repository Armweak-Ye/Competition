# bomb.py — 排爆区模块（爆炸物定位 + 排爆桶检测）
# 由 main.py 调用，爆炸物和排爆桶分开执行

import sensor
import image

_sensor_ready = False

# 测距标定常数 — 运行 calibrate.py 标定后替换
K_BOMB = 3600


def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False

# HSV 颜色阈值 — 赛场现场用 Threshold Editor 标定！
RED_THRESHOLD   = (0, 45, 40, 80, 20, 80)     # 红色 C0 M100 Y100 K0
GREEN_THRESHOLD = (25, 75, -80, -20, 5, 60)   # 绿色 C80 M0 Y100 K0
BLUE_THRESHOLD  = (15, 55, -10, 50, -80, -30) # 蓝色 C100 M0 Y0 K0
BLACK_THRESHOLD = (0, 60, -128, 127, -128, -20)  # 黑色排爆桶


def _init_sensor():
    global _sensor_ready
    if _sensor_ready:
        return
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.VGA)
    sensor.skip_frames(60)
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    _sensor_ready = True


def _quant(v):
    return min(255, max(0, v))


def _distance_from_width(pixel_width):
    """距离(cm) = K / 像素宽度"""
    if pixel_width <= 0:
        return 0
    dist = int(K_BOMB / pixel_width)
    return min(255, max(0, dist))


def _pick_bomb(blobs):
    """从同色 blobs 中选出最像爆炸物的（圆形度 > 0.4 且面积最大）"""
    if not blobs:
        return None
    candidates = [b for b in blobs if b.roundness() > 0.4]
    if candidates:
        return max(candidates, key=lambda b: b.area())
    return max(blobs, key=lambda b: b.area())


def detect_bomb(color):
    """
    检测指定颜色的爆炸物。

    参数:
        color: 1=红, 2=绿, 3=蓝

    返回:
        (X, Y, Dist)  各为 0~255，0=未找到
    """
    _init_sensor()

    if color == 1:
        threshold = RED_THRESHOLD
    elif color == 2:
        threshold = GREEN_THRESHOLD
    elif color == 3:
        threshold = BLUE_THRESHOLD
    else:
        threshold = RED_THRESHOLD

    for _ in range(5):
        img = sensor.snapshot()
        img.lens_corr(1.5)

        blobs = img.find_blobs([threshold], pixels_threshold=80,
                                area_threshold=80, merge=True)
        bomb = _pick_bomb(blobs)

        if bomb:
            X = _quant(bomb.cx())
            Y = _quant(bomb.cy())
            Dist = _distance_from_width(bomb.w())
        else:
            X, Y, Dist = 0, 0, 0

        return (X, Y, Dist)

    return None


def detect_bin():
    """
    检测黑色排爆桶。

    返回:
        (binX, binY)  各为 0~255，0=未找到
    """
    _init_sensor()

    for _ in range(5):
        img = sensor.snapshot()
        img.lens_corr(1.5)

        bin_blobs = img.find_blobs([BLACK_THRESHOLD], pixels_threshold=300,
                                    area_threshold=400, merge=True)
        if bin_blobs:
            bin_b = max(bin_blobs, key=lambda b: b.cy() + b.h())
            binX = _quant(bin_b.cx())
            binY = _quant(bin_b.cy())
        else:
            binX, binY = 0, 0

        return (binX, binY)

    return None
