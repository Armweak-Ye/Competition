# target.py — 反恐区模块（靶标颜色识别 + 圆心定位）
# 由 main.py 调用

import sensor
import time

_sensor_ready = False
clock = time.clock()

# 曝光下调系数 — 补光过曝时调小（0.5~0.8），欠曝时调大（1.0 表示不降）
EXPOSURE_SCALE = 0.6

# ==================== 夹取点位判断范围（QVGA 原始像素坐标，改这里）====================
# 注：QVGA 画面为 320x240，x 范围 0~319，y 范围 0~239
# 以下为按 VGA 值等比换算的临时值，必须实测重新标定
GRAB_X_MIN = 131
GRAB_X_MAX = 141
GRAB_Y_MIN = 126
GRAB_Y_MAX = 132

# ================= 目标识别 ROI（2026-10-16 新增）=================
# 坐标是【QVGA 320x240】下的（OpenMV IDE 框选得到）：(x, y, w, h)
#   (1) 只在框内找色块：框外的色块直接不看；部分出框的色块会被"裁剪"、
#       中心点会跟着偏 —— 所以框要保证靶标【完整】在里面，四周建议留 20~30px
#   (2) 77x72 只占整帧约 7%，扫描快约 10 倍；detect_target() 每轮最多取 5 帧，
#       帧率越高越容易在行进中抓到"X 进窗口"的正确时刻
#   (3) 注意：以后若改 set_framesize()，这组坐标要按比例换算
TARGET_ROI = (103, 100, 77, 72)

# 调试开关：1 = 在画面上画黄框（标定 ROI 位置用）；0 = 不画
TARGET_DRAW_ROI = 1

# ROI 内没找到时是否整帧兜底再找一次：
#   1 = 更稳（判据窗口只有约 10x6 像素，误检风险很低；而漏检会让整个反恐任务被保底跳过）
#   0 = 严格只在 ROI 内识别
TARGET_ROI_FALLBACK_FULL = 0


def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False


# HSV 颜色阈值 — 赛场现场用 Threshold Editor 标定！
RED_THRESHOLD = (18, 38, 16, 63, -12, 44)     # 红色外环 C0 M100 Y100 K0（L 上限和 A/B 下限都放宽，兼容过曝）
GREEN_THRESHOLD = (21, 54, -64, -11, 18, 60)   # 绿色外环 C80 M0 Y100 K0
BLUE_THRESHOLD = (20, 46, -30, 14, -52, -11)  # 蓝色外环 C100 M0 Y0 K0


def _init_sensor():
    global _sensor_ready
    if _sensor_ready:
        return
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(60)                    # 先让自动曝光收敛
    auto_exp = sensor.get_exposure_us()       # 读出当前曝光值
    sensor.set_auto_exposure(False, exposure_us=int(auto_exp * EXPOSURE_SCALE))
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    sensor.skip_frames(10)
    _sensor_ready = True


def _quant_x(v):
    return min(255, max(0, v * 255 // 319))


def _quant_y(v):
    return min(255, max(0, v * 255 // 239))


def _in_grab_zone(x, y):
    """判断目标中心是否到达夹取点位"""
    return GRAB_X_MIN < x < GRAB_X_MAX and GRAB_Y_MIN < y < GRAB_Y_MAX


def detect_target(color):
    """
    检测指定颜色的靶标，定位圆心。

    参数:
        color: 1=红, 2=绿, 3=蓝

    返回:
        (tX, tY, flag)  圆心缩放坐标 + flag，flag=1 表示到达夹取点位
    """
    _init_sensor()

    if color == 1:
        threshold = RED_THRESHOLD
    elif color == 2:
        threshold = GREEN_THRESHOLD
    elif color == 3:
        threshold = BLUE_THRESHOLD
    else:
        print("[TARGET] invalid color=%r, fallback RED" % (color,))
        threshold = RED_THRESHOLD

    for _ in range(5):
        img = sensor.snapshot()
        clock.tick()

        # 画夹取点位置（绿十字），方便现场标定 GRAB 范围
        img.draw_cross((GRAB_X_MIN + GRAB_X_MAX) // 2,
                       (GRAB_Y_MIN + GRAB_Y_MAX) // 2,
                       color=(0, 255, 0), size=10, thickness=1)

        # ---- 颜色分割找外环：先只在 ROI 内找 ----
        #     find_blobs 的 ROI 是关键字参数（第一个位置参数是阈值表），
        #     不能写成 find_blobs([threshold], [TARGET_ROI]) 那种形式
        blobs = img.find_blobs([threshold], roi=TARGET_ROI,
                               pixels_threshold=50,
                               area_threshold=50, merge=True, margin=5)

        # ROI 内没找到 -> 整帧兜底再找一次（TARGET_ROI_FALLBACK_FULL=0 则跳过，严格只认 ROI）
        if not blobs and TARGET_ROI_FALLBACK_FULL:
            blobs = img.find_blobs([threshold], pixels_threshold=50,
                                   area_threshold=50, merge=True, margin=5)

        if TARGET_DRAW_ROI:
            img.draw_rectangle(TARGET_ROI, color=(255, 255, 0))   # 黄框 = 设定的识别 ROI

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
            threshold=3500,
            x_margin=10, y_margin=10,
            r_margin=10,
            r_min=3, r_max=45,
            roi=(x1, y1, x2 - x1, y2 - y1)
        )

        # 靶心 = 红环几何中心。只接受圆心离它不超过色块 1/6 尺寸的圆，
        # 偏在环边上的假圆一律丢弃。
        blob_cx, blob_cy = target_blob.cx(), target_blob.cy()
        max_offset = max(target_blob.w(), target_blob.h()) // 6

        candidates = [c for c in circles
                      if (c.x() - blob_cx) ** 2 + (c.y() - blob_cy) ** 2
                      <= max_offset ** 2]

        if candidates:
            best = min(candidates, key=lambda c: (c.x() - blob_cx) ** 2 +
                                                 (c.y() - blob_cy) ** 2)
            img.draw_circle(best.x(), best.y(), best.r(), color=(0, 255, 0))
            raw_x, raw_y = best.x(), best.y()
        else:
            # 没有可信的圆，退回色块中心（外环对称，中心即靶心）
            raw_x, raw_y = blob_cx, blob_cy

        tX = _quant_x(raw_x)
        tY = _quant_y(raw_y)
        flag = 1 if _in_grab_zone(raw_x, raw_y) else 0

        info = "TARGET X=%d Y=%d W=%d %s" % (target_blob.cx(), target_blob.cy(),
                                             target_blob.w(), "HIT" if flag else "")
        img.draw_string(target_blob.x() + 2, target_blob.y() - 14, info, color=(255, 0, 0))
        img.draw_string(0, 0, "FPS:%.1f" % clock.fps())
        return (tX, tY, flag)

    return None
