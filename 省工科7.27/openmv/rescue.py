# rescue2.py — 救援区模块（blob 引导 + 模板匹配确认）
# 由 main.py 调用
#
# 模板文件: 01.pgm(圆柱) 02.pgm(圆锥) 03.pgm(腰鼓)

import sensor
import image

_sensor_ready = False
_template = None

MATCH_THRESHOLD = 0.9
ROI = (245, 165, 150, 150)   # VGA 中心区域
TOLERANCE = 5               # 偏离 ROI 中心 ±5px 以内算居中


def reset_module():
    global _sensor_ready, _template
    _sensor_ready = False
    _template = None


def _init_sensor():
    global _sensor_ready
    if _sensor_ready:
        return
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.VGA)
    sensor.skip_frames(60)
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    _sensor_ready = True


def _quant_x(v):
    return min(255, max(0, v * 255 // 639))


def _quant_y(v):
    return min(255, max(0, v * 255 // 479))


def detect_rescue(target_shape):
    """
    target_shape: 1=圆柱, 2=圆锥, 3=腰鼓

    返回: (X, Y, Dist, confirmed)
      confirmed = 0: 引导居中 / 未确认
      confirmed = 1: 模板确认，可以抓
    """
    global _template

    _init_sensor()

    if _template is None:
        _template = image.Image("0%d.pgm" % target_shape, copy_to_fb=True)

    for _ in range(3):
        img = sensor.snapshot()

        blobs = img.find_blobs([(200, 255)], pixels_threshold=200,
                                area_threshold=300, merge=True)
        if not blobs:
            continue

        b = max(blobs, key=lambda x: x.area())

        rx, ry, rw, rh = ROI
        roi_cx = rx + rw // 2    # ROI 中心 X
        roi_cy = ry + rh // 2    # ROI 中心 Y

        centered = (abs(b.cx() - roi_cx) <= TOLERANCE) and \
                   (abs(b.cy() - roi_cy) <= TOLERANCE)

        if not centered:
            return (_quant_x(b.cx()), _quant_y(b.cy()), 0, 0)

        # blob 居中 → 模板匹配确认
        x1 = max(0, b.x() - 10)
        y1 = max(0, b.y() - 10)
        x2 = min(img.width(), b.x() + b.w() + 10)
        y2 = min(img.height(), b.y() + b.h() + 10)

        r = img.find_template(_template, MATCH_THRESHOLD, step=2,
                               search=image.SEARCH_EX,
                               roi=(x1, y1, x2 - x1, y2 - y1))
        if r:
            X = _quant_x(r.x() + _template.width() // 2)
            Y = _quant_y(r.y() + _template.height() // 2)
            return (X, Y, 0, 1)

        return (_quant_x(b.cx()), _quant_y(b.cy()), 0, 0)

    return None
