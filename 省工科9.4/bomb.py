# bomb.py — 排爆区模块（爆炸物定位 + 排爆桶检测）
# 由 main.py 调用，爆炸物和排爆桶分开执行

import sensor

_sensor_ready = False

# ==================== 夹取点位判断范围（原始像素坐标，改这里）====================
GRAB_X_MIN = 200
GRAB_X_MAX = 205
GRAB_Y_MIN = 250
GRAB_Y_MAX = 255


def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False


# HSV 颜色阈值 — 赛场现场用 Threshold Editor 标定！
RED_THRESHOLD = (0, 45, 40, 80, 20, 80)  # 红色 C0 M100 Y100 K0
GREEN_THRESHOLD = (25, 75, -80, -20, 5, 60)   # 绿色 C80 M0 Y100 K0
BLUE_THRESHOLD = (15, 55, -10, 50, -80, -30)  # 蓝色 C100 M0 Y0 K0
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


def _quant_x(v):
    return min(255, max(0, v * 255 // 639))


def _quant_y(v):
    return min(255, max(0, v * 255 // 479))


def _in_grab_zone(x, y):
    """判断目标中心是否到达夹取点位"""
    return GRAB_X_MIN < x < GRAB_X_MAX and GRAB_Y_MIN < y < GRAB_Y_MAX


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
        (X, Y, flag)  X/Y 为缩放后坐标 0~255，flag=1 表示到达夹取点位
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

        blobs = img.find_blobs([threshold], pixels_threshold=80,
                               area_threshold=80, merge=True)
        bomb = _pick_bomb(blobs)

        if bomb:
            raw_x, raw_y = bomb.cx(), bomb.cy()
            # 画识别框 + 数据
            img.draw_rectangle(bomb.rect())
            img.draw_cross(raw_x, raw_y)
            info = "X=%d Y=%d W=%d" % (raw_x, raw_y, bomb.w())
            img.draw_string(bomb.x() + 2, bomb.y() - 14, info, color=(255, 0, 0))
            img.draw_string(0, 0, "FPS:%.1f" % sensor.get_fps())
            X = _quant_x(raw_x)
            Y = _quant_y(raw_y)
            flag = 1 if _in_grab_zone(raw_x, raw_y) else 0
        else:
            X, Y, flag = 0, 0, 0

        return (X, Y, flag)

    return None


def detect_bin():
    """
    检测黑色排爆桶。

    返回:
        (binX, binY, flag)  flag=1 表示到达投放点位
    """
    _init_sensor()

    for _ in range(5):
        img = sensor.snapshot()

        bin_blobs = img.find_blobs([BLACK_THRESHOLD], pixels_threshold=300,
                                   area_threshold=400, merge=True)
        if bin_blobs:
            bin_b = max(bin_blobs, key=lambda b: b.cy() + b.h())
            raw_x, raw_y = bin_b.cx(), bin_b.cy()
            img.draw_rectangle(bin_b.rect())
            info = "BIN X=%d Y=%d" % (raw_x, raw_y)
            img.draw_string(bin_b.x() + 2, bin_b.y() - 14, info, color=(255, 0, 0))
            img.draw_string(0, 0, "FPS:%.1f" % sensor.get_fps())
            binX = _quant_x(raw_x)
            binY = _quant_y(raw_y)
            flag = 1 if _in_grab_zone(raw_x, raw_y) else 0
        else:
            binX, binY, flag = 0, 0, 0

        return (binX, binY, flag)

    return None
