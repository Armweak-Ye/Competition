# bomb.py — 排爆区模块（爆炸物定位 + 排爆桶检测）
# 由 main.py 调用，爆炸物和排爆桶分开执行

import sensor
import time

_sensor_ready = False
_active_scale = None
clock = time.clock()

# 曝光下调系数 — 补光过曝时调小（0.5~0.8），欠曝时调大（1.0 表示不降）
EXPOSURE_SCALE = 0.7        # 排爆物（彩色）用
BIN_EXPOSURE_SCALE = 0.9    # 排爆桶（黑色）用 — 阴影被误检时调大，直到阴影不入阈值

# ==================== 夹取点位判断范围（QVGA 原始像素坐标，改这里）====================
# 注：QVGA 画面为 320x240，x 范围 0~319，y 范围 0~239
# 以下为按 VGA 值等比换算的临时值，必须实测重新标定
GRAB_X_MIN = 119
GRAB_X_MAX = 135
GRAB_Y_MIN = 154
GRAB_Y_MAX = 170


def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False

# HSV 颜色阈值 — 赛场现场用 Threshold Editor 标定！
RED_THRESHOLD = (5, 36, 9, 52, -8, 44)  # 红色 C0 M100 Y100 K0（L 上限和 A/B 下限都放宽，兼容过曝）
GREEN_THRESHOLD = (16, 48, -60, -27, 4, 61)   # 绿色 C80 M0 Y100 K0
BLUE_THRESHOLD = (7, 31, -26, 50, -55, -18)  # 蓝色 C100 M0 Y0 K0
# 黑色排爆桶 — A/B 放宽到中性范围，避免漏检中性黑
BLACK_THRESHOLD = (2, 8, -8, 127, -44, 52)


def _init_sensor(scale):
    """按指定曝光系数初始化传感器；系数变化时会重新初始化"""
    global _sensor_ready, _active_scale
    if _sensor_ready and _active_scale == scale:
        return
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(60)                    # 先让自动曝光收敛
    auto_exp = sensor.get_exposure_us()       # 读出当前曝光值
    sensor.set_auto_exposure(False, exposure_us=int(auto_exp * scale))
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    sensor.skip_frames(10)
    _sensor_ready = True
    _active_scale = scale


def _quant_x(v):
    return min(255, max(0, v * 255 // 319))


def _quant_y(v):
    return min(255, max(0, v * 255 // 239))


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
    _init_sensor(EXPOSURE_SCALE)

    if color == 1:
        threshold = RED_THRESHOLD
    elif color == 2:
        threshold = GREEN_THRESHOLD
    elif color == 3:
        threshold = BLUE_THRESHOLD
    else:
        print("[BOMB] invalid color=%r, fallback RED" % (color,))
        threshold = RED_THRESHOLD

    for _ in range(5):
        img = sensor.snapshot()
        clock.tick()

        # 画夹取点位置（绿十字），方便现场标定 GRAB 范围
        img.draw_cross((GRAB_X_MIN + GRAB_X_MAX) // 2,
                       (GRAB_Y_MIN + GRAB_Y_MAX) // 2,
                       color=(0, 255, 0), size=10, thickness=1)

        blobs = img.find_blobs([threshold], pixels_threshold=40,
                               area_threshold=50, merge=True)
        bomb = _pick_bomb(blobs)

        if bomb:
            raw_x, raw_y = bomb.cx(), bomb.cy()
            flag = 1 if _in_grab_zone(raw_x, raw_y) else 0
            # 画识别框 + 数据
            img.draw_rectangle(bomb.rect())
            img.draw_cross(raw_x, raw_y)
            info = "BOMB X=%d Y=%d W=%d %s" % (raw_x, raw_y, bomb.w(),
                                               "HIT" if flag else "")
            img.draw_string(bomb.x() + 2, bomb.y() - 14, info, color=(255, 0, 0))
            img.draw_string(0, 0, "FPS:%.1f" % clock.fps())
            X = _quant_x(raw_x)
            Y = _quant_y(raw_y)
        else:
            img.draw_string(0, 0, "FPS:%.1f  BOMB not found" % clock.fps())
            X, Y, flag = 0, 0, 0

        return (X, Y, flag)

    return None


def detect_bin():
    """
    检测黑色排爆桶。

    返回:
        (binX, binY, flag)  flag=1 表示到达投放点位
    """
    _init_sensor(BIN_EXPOSURE_SCALE)

    for _ in range(5):
        img = sensor.snapshot()
        img.lens_corr(1.5)
        clock.tick()

        bin_blobs = img.find_blobs([BLACK_THRESHOLD], pixels_threshold=75,
                                   area_threshold=100, merge=True)

        # 画夹取点位置（绿十字），方便现场标定 GRAB 范围
        zone_cx = (GRAB_X_MIN + GRAB_X_MAX) // 2
        zone_cy = (GRAB_Y_MIN + GRAB_Y_MAX) // 2
        img.draw_cross(zone_cx, zone_cy, color=(0, 255, 0), size=10, thickness=1)

        if bin_blobs:
            # 几何筛选：排爆桶是正圆、宽高比接近1、悬在画面中不贴边
            # （贴边的大暗块是桌面/地面阴影，直接排除）
            img_w, img_h = img.width(), img.height()
            cands = []
            for b in bin_blobs:
                w, h = b.w(), b.h()
                if w <= 0 or h <= 0:
                    continue
                if not (0.7 <= w / h <= 1.4):          # 宽高比接近 1
                    continue
                if b.roundness() < 0.35:               # 圆形度够
                    continue
                if (b.x() <= 2 or b.y() <= 2 or
                        b.x() + w >= img_w - 2 or b.y() + h >= img_h - 2):
                    continue                           # 贴边的一律排除
                cands.append(b)
            bin_b = max(cands, key=lambda b: b.area()) if cands else None
        else:
            bin_b = None

        if bin_b:
            raw_x, raw_y = bin_b.cx(), bin_b.cy()
            flag = 1 if _in_grab_zone(raw_x, raw_y) else 0
            # 画识别框 + 十字 + 数据
            img.draw_rectangle(bin_b.rect())
            img.draw_cross(raw_x, raw_y)
            info = "BIN X=%d Y=%d W=%d %s" % (raw_x, raw_y, bin_b.w(),
                                              "HIT" if flag else "")
            img.draw_string(bin_b.x() + 2, bin_b.y() - 14, info, color=(255, 0, 0))
            img.draw_string(0, 0, "FPS:%.1f" % clock.fps())
            binX = _quant_x(raw_x)
            binY = _quant_y(raw_y)
        else:
            img.draw_string(0, 0, "FPS:%.1f  BIN not found" % clock.fps())
            binX, binY, flag = 0, 0, 0

        return (binX, binY, flag)

    return None
