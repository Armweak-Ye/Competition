# target.py — 反恐区模块（靶标颜色识别 + 圆心定位 + 测距）
# 由 main.py 调用

import sensor
import image

_sensor_ready = False

# 测距标定常数 — 用靶标外环直径运行 calibrate.py 标定后替换
K_TARGET = 3600


def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False

# HSV 颜色阈值 — 赛场现场用 Threshold Editor 标定！
RED_THRESHOLD   = (0, 45, 40, 80, 20, 80)     # 红色外环 C0 M100 Y100 K0
GREEN_THRESHOLD = (25, 75, -80, -20, 5, 60)   # 绿色外环 C80 M0 Y100 K0
BLUE_THRESHOLD  = (15, 55, -10, 50, -80, -30) # 蓝色外环 C100 M0 Y0 K0


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


def _distance_from_width(pixel_width):
    """距离(cm) = K / 像素宽度"""
    if pixel_width <= 0:
        return 0
    dist = int(K_TARGET / pixel_width)
    return min(255, max(0, dist))


def detect_target(color):
    """
    检测指定颜色的靶标，定位圆心并测距。

    参数:
        color: 1=红, 2=绿, 3=蓝

    返回:
        (tX, tY, Dist)  圆心坐标 + 距离厘米数，0~255，0=未找到
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

        # ---- 颜色分割找外环 ----
        blobs = img.find_blobs([threshold], pixels_threshold=200,
                                area_threshold=200, merge=True)
        if not blobs:
            continue

        target_blob = max(blobs, key=lambda b: b.area())
        img.draw_rectangle(target_blob.rect())

        # ---- 在色块区域内做圆检测找圆心 ----
        x1 = max(0, target_blob.x() - 20)
        y1 = max(0, target_blob.y() - 20)
        x2 = min(img.width(), target_blob.x() + target_blob.w() + 20)
        y2 = min(img.height(), target_blob.y() + target_blob.h() + 20)

        circles = img.find_circles(
            threshold=3000,
            x_margin=10, y_margin=10,
            r_margin=10,
            r_min=3, r_max=80,
            roi=(x1, y1, x2 - x1, y2 - y1)
        )

        if circles:
            for c in circles:
                img.draw_circle(c.x(), c.y(), c.r(), color=(0, 255, 0))
            sum_x = sum(c.x() for c in circles)
            sum_y = sum(c.y() for c in circles)
            n = len(circles)
            tX = _quant_x(sum_x // n)
            tY = _quant_y(sum_y // n)
        else:
            tX = _quant_x(target_blob.cx())
            tY = _quant_y(target_blob.cy())

        info = "X=%d Y=%d W=%d" % (target_blob.cx(), target_blob.cy(), target_blob.w())
        img.draw_string(target_blob.x() + 2, target_blob.y() - 14, info, color=(255,0,0))
        img.draw_string(0, 0, "FPS:%.1f" % sensor.get_fps())
        Dist = _distance_from_width(target_blob.w())
        return (tX, tY, Dist)

    return None
