# line.py — 巡线模块（紫色赛道中心定位）
# 由 main.py 调用。辅助小车直线行驶，防止跑偏。
#
# 原理：摄像头在机械臂固定姿态下斜向下看到紫色赛道；在画面下方取一条水平窄带，
#       找该带内紫色区域的水平中点，量化成 0~255 后连同“是否找到”标志一起上报主控；
#       主控拿它和设定值求差，用麦克纳姆轮做横向纠正。
#       车头朝向由陀螺仪单独负责，本模块只提供横向位置参考。

import sensor
import time

_sensor_ready = False
clock = time.clock()

# ==================== 紫色赛道阈值（LAB，现场用 Threshold Editor 标定！）====================
# 紫色在 LAB 中的特征：a 偏正（红紫方向）、b 偏负（蓝方向）
PURPLE_THRESHOLD = (41, 68, -25, 14, -23, 3)

# ==================== 采样 ROI（画面上的一条水平窄带，只看这里）====================
# 只看这一条带：避开远处透视畸变，也避开画面最下端可能被车身/夹爪挡住的部分
# QVGA 画面为 320x240，x 范围 0~319、y 范围 0~239
# 以下均为默认值，务必对着实际画面调整
ROI_X = 10      # ROI 左边界：(320-230)//2 = 45 → 水平居中（左右各留 45）
ROI_Y = 158     # ROI 上边界：保持原来采样带的垂直中心(184)不变 → 159~209
ROI_W = 304     # ROI 宽度 230
ROI_H = 50      # ROI 高度 50（下边界 209 ≤ 240，不越界）
ROI = (ROI_X, ROI_Y, ROI_W, ROI_H)

# 紫色区域最小像素数 / 面积（滤掉噪点）
MIN_PIXELS = 100
MIN_AREA = 150

# ==================== 需要对齐的 X（设定值）====================
# 单位 = 原始像素 0~319（和画面里读到的 center 同一坐标系，不做任何量化换算）
# 画面正中 = 160；实车对中时几乎不会是 160，必须实测后填。
# 注：发给主控的 X 是量化值，主控那边的设定值 = SETPOINT_X * 255 // 319
#     当前实车标定：车身居中时主控量化值 = 130
#     反算到原始像素：130 * 319 / 255 ≈ 163
SETPOINT_X = 180

# 两条参考线的颜色（RGB565）
X_LINE_COLOR        = (0, 255, 0)     # 实测 X（绿）
SETPOINT_LINE_COLOR = (255, 0, 0)     # 设定值（红）

# ==================== 绘制开关（True=画，False=不画）====================
# 每个功能一个独立开关，互不影响
DRAW_ROI      = True   # 采样 ROI 框（蓝框）
DRAW_TRACK    = True   # 识别到的紫色跨度（框）+ 中心十字（绿）
DRAW_X        = True   # 在“本次求得的 X”处画一条细竖线（绿，原始像素坐标）
DRAW_SETPOINT = True   # 在“设定值 SETPOINT_X”处画一条细竖线（红，只画在 ROI 内）
DRAW_TEXT     = True   # 主文字标签（raw / sp / d / W，全部原始像素）
DRAW_MCU_TEXT = True   # 额外一行给主控填参数的量化值（只影响文字，不影响画线）


def reset_module():
    """供 main.py 在模式切换时调用"""
    global _sensor_ready
    _sensor_ready = False


def _init_sensor():
    global _sensor_ready
    if _sensor_ready:
        return
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)      # 颜色分割需要彩色
    sensor.set_framesize(sensor.QVGA)        # 巡线要快，用 QVGA
    sensor.skip_frames(60)
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)
    _sensor_ready = True


def _quant_x(v):
    return min(255, max(0, v * 255 // 319))


def detect_line():
    """
    检测紫色赛道的水平中心。

    返回: (X, flag)
        X    = 赛道中心量化坐标 0~255
        flag = 1 本帧有效（找到赛道）
               0 未找到（赛道丢失/反光/出赛道，主控应保持上次纠偏量或减速）
    """
    _init_sensor()

    img = sensor.snapshot()
    clock.tick()

    # 只在采样 ROI 内找紫色色块
    blobs = img.find_blobs([PURPLE_THRESHOLD], roi=ROI,
                           pixels_threshold=MIN_PIXELS,
                           area_threshold=MIN_AREA,
                           merge=True, margin=20)

    # 设定值夹到画面范围内（画线与文字都用它，保证两者一致）
    sp_raw = min(img.width() - 1, max(0, SETPOINT_X))

    if DRAW_ROI:
        img.draw_rectangle(ROI, color=127)

    # 设定值参考线：先画，丢线时也保留 —— 方便判断“线本来应该在哪”
    if DRAW_SETPOINT:
        img.draw_line(sp_raw, ROI_Y, sp_raw, ROI_Y + ROI_H,
                      color=SETPOINT_LINE_COLOR, thickness=1)

    if not blobs:
        if DRAW_TEXT:
            img.draw_string(ROI_X + 2, ROI_Y - 16,
                            "LINE not found  sp=%d" % sp_raw, color=255)
            img.draw_string(0, 0, "FPS:%.1f" % clock.fps())
        return (0, 0)

    # 取所有紫色块的“整体跨度”：最左到最右，再算中点
    # （比取单个最大块的质心更稳，赛道被反光切断也能还原）
    left = min(b.x() for b in blobs)
    right = max(b.x() + b.w() for b in blobs)
    center = ((left + right) + 20) // 2

    if DRAW_TRACK:
        img.draw_rectangle((left, ROI_Y, right - left, ROI_H), color=255)
        img.draw_cross(center, ROI_Y + ROI_H // 2, color=(0, 255, 0))

    # 实测 X 参考线：与设定值同一条 y 区间，一眼看出左右偏了多少
    if DRAW_X:
        img.draw_line(center, ROI_Y, center, ROI_Y + ROI_H,
                      color=X_LINE_COLOR, thickness=1)

    if DRAW_TEXT:
        img.draw_string(ROI_X + 2, ROI_Y - 16,
                        "LINE raw=%d sp=%d d=%d W=%d"
                        % (center, sp_raw, center - sp_raw, right - left),
                        color=255)
        img.draw_string(0, 0, "FPS:%.1f" % clock.fps())

    if DRAW_MCU_TEXT:
        img.draw_string(ROI_X + 2, ROI_Y - 30,
                        "MCU X=%d sp=%d" % (_quant_x(center), _quant_x(sp_raw)),
                        color=255)

    return (_quant_x(center), 1)
