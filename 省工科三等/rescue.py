# rescue.py — 救援区模块（blob 引导 + 模板匹配确认）
# 由 main.py 调用
#
# 模板文件: 01.pgm(圆柱) 02.pgm(圆锥) 03.pgm(腰鼓)

import sensor
import image
import time

_sensor_ready = False
_template = None
_template_shape = None
clock = time.clock()

MATCH_THRESHOLD = 0.78

# 模板匹配搜索步长 — 越大越快、精度越低
# step=2 每帧要算上亿次，帧率会掉到 1 fps 以下；8~10 在帧率和精度间较平衡
MATCH_STEP = 10

# 模板匹配搜索框：在白色色块四周外扩的像素数
# 白块（阈值 239~255）通常只覆盖目标最亮的核心，比实际物体小，
# 外扩大一些才能把整个模板装进去
MATCH_ROI_MARGIN = 50

# ==================== 夹取点位（VGA 原始像素坐标，改这里）====================
# VGA 画面 640x480。当前夹取点中心 (287, 292)，容差 ±10
GRAB_X_MIN = 277
GRAB_X_MAX = 297
GRAB_Y_MIN = 282
GRAB_Y_MAX = 302

# ==================== 居中判断 ROI ====================
# VGA 640x480 原始像素坐标：(x, y, w, h)
# 物体只要进入这个框，就允许启动模板匹配；精确的抓取判定仍看上面的夹取点
ROI = (183, 188, 232, 269)

# ==================== 白色检测区域（只检测画面上 4/5，下部 1/5 不检测）====================
# VGA 高 480，上 4/5 → y 从 0 到 384。调这里可以改变检测范围
DETECT_Y_MAX = 384

# ==================== 绘制开关（True=画，False=不画）====================
DRAW_ROI = True      # ROI 参考框（灰框）
DRAW_CROSS = False     # 夹取点绿十字
DRAW_BLOB = False     # 白色检测框 + 中心十字
DRAW_MATCH = True     # 模板匹配框（白框）
DRAW_TEXT = True      # 所有文字标签


def reset_module():
    global _sensor_ready, _template, _template_shape
    _sensor_ready = False
    _template = None
    _template_shape = None


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


def _in_grab_zone(x, y):
    """判断目标中心是否到达夹取点位"""
    return GRAB_X_MIN < x < GRAB_X_MAX and GRAB_Y_MIN < y < GRAB_Y_MAX


def detect_rescue(target_shape):
    """
    target_shape: 1=圆柱, 2=圆锥, 3=腰鼓

    返回: (X, Y, flag)
      flag = 0: 未到达夹取点位
      flag = 1: 到达夹取点位，可以抓
    """
    global _template, _template_shape

    if target_shape not in (1, 2, 3):
        print("[RESCUE] invalid shape=%r, fallback 1" % (target_shape,))
        target_shape = 1

    _init_sensor()

    if _template is None or _template_shape != target_shape:
        # 不要加 copy_to_fb！否则模板会占帧缓冲区，被 sensor.snapshot() 覆盖
        _template = image.Image("0%d.pgm" % target_shape)
        _template_shape = target_shape

    for _ in range(3):
        img = sensor.snapshot()
        clock.tick()

        # 画夹取点位置（绿十字），方便现场标定 GRAB 范围
        if DRAW_CROSS:
            img.draw_cross((GRAB_X_MIN + GRAB_X_MAX) // 2,
                           (GRAB_Y_MIN + GRAB_Y_MAX) // 2,
                           color=(0, 255, 0), size=12, thickness=1)

        # 白色检测只在画面上 4/5 进行，下部 1/5 不检测
        blobs = img.find_blobs([(157, 255)], pixels_threshold=200,
                               area_threshold=300, merge=True,
                               roi=ROI)
        if not blobs:
            if DRAW_TEXT:
                img.draw_string(0, 0, "FPS:%.1f  RESCUE not found" % clock.fps())
            continue

        b = max(blobs, key=lambda x: x.area())
        raw_x, raw_y = b.cx(), b.cy()
        flag = 0
        matched = False
        match_rect = None
        label = ""

        rx, ry, rw, rh = ROI

        # 画 ROI 参考框（由 DRAW_ROI 控制开关）
        if DRAW_ROI:
            img.draw_rectangle(ROI, color=127)

        in_roi = (rx <= raw_x <= rx + rw) and (ry <= raw_y <= ry + rh)

        if not in_roi:
            label = "OUT X=%d Y=%d" % (raw_x, raw_y)
        else:
            # 物体进入 ROI → 模板匹配确认（搜索框在色块四周外扩 MARGIN 像素）
            x1 = max(0, b.x() - MATCH_ROI_MARGIN)
            y1 = max(0, b.y() - MATCH_ROI_MARGIN)
            x2 = min(img.width(), b.x() + b.w() + MATCH_ROI_MARGIN)
            y2 = min(img.height(), b.y() + b.h() + MATCH_ROI_MARGIN)
            roi_w, roi_h = x2 - x1, y2 - y1

            # 搜索框装不下模板 → 目标太小（离得远），跳过匹配
            if roi_w < _template.width() or roi_h < _template.height():
                label = "FAR blob=%dx%d tpl=%dx%d" % (b.w(), b.h(),
                                                      _template.width(),
                                                      _template.height())
            else:
                r = img.find_template(_template, MATCH_THRESHOLD, step=MATCH_STEP,
                                      search=image.SEARCH_EX,
                                      roi=(x1, y1, roi_w, roi_h))
                if r:
                    matched = True

                    if hasattr(r, "rect"):
                        # 旧版 OpenMV：find_template 返回 match 对象
                        match_rect = r.rect()
                        rx0, ry0 = r.x(), r.y()
                        score_text = "s=%.2f " % r.score()
                    else:
                        # OpenMV v4.7.0：find_template 返回 tuple=(x,y,w,h[,score])
                        rx0, ry0 = r[0], r[1]
                        rw, rh = r[2], r[3]
                        match_rect = (rx0, ry0, rw, rh)
                        score_text = ""

                    raw_x = rx0 + _template.width() // 2
                    raw_y = ry0 + _template.height() // 2
                    # flag=1 条件：匹配成功且 X 落在夹取点 X 范围内
                    flag = 1 if (GRAB_X_MIN <= raw_x <= GRAB_X_MAX) else 0
                    label = "MATCH X=%d Y=%d %s%s" % (
                        raw_x,
                        raw_y,
                        score_text,
                        "HIT" if flag else ""
                    )
                else:
                    label = "X=%d Y=%d NO" % (raw_x, raw_y)

        # ---- 画框：匹配到用绿框，否则用白色色块框 ----
        if matched:
            if DRAW_MATCH:
                img.draw_rectangle(match_rect, color=(0, 255, 0))
        else:
            if DRAW_BLOB:
                img.draw_rectangle(b.rect(), color=255)
                img.draw_cross(b.cx(), b.cy())

        if DRAW_TEXT:
            img.draw_string(b.x() + 2, b.y() - 14, label, color=255)
            img.draw_string(0, 0, "FPS:%.1f" % clock.fps())

        return (_quant_x(raw_x), _quant_y(raw_y), flag)

    return None
