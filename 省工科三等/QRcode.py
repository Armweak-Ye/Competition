# QRcode.py — 二维码扫描模块
# 由 main.py 调用

import sensor

_sensor_ready = False

# ================= 二维码识别 ROI（2026-10-16 新增）=================
# 只在这个矩形里找二维码：(x, y, w, h)，坐标是【VGA 640x480】下的（OpenMV IDE 框选得到）
#   (1) 二维码必须【完整】落在 ROI 内才会被识别：只要有一部分出框就找不到
#       -> 框要比二维码本身大一圈，四周建议各留 20~30px 余量
#   (2) 只在 ROI 内扫描，像素数约为整帧 VGA 的 20%，速度快 3~5 倍；
#       main.py 的 mode_qr() 是"一直重试"的，试得越快越不容易漏
#   (3) 注意：以后若改 sensor.set_framesize()（例如 QVGA 320x240），
#       这组坐标必须按比例换算，否则会框在错误位置
QR_ROI = (392, 200, 400, 370)

# 调试开关：1 = 在画面上画出 ROI 框和识别结果（标定时看）；0 = 不画（比赛时可关，省几毫秒）
QR_DRAW_DEBUG = 1

# ROI 里没找到时，是否再用整帧兜底找一次：
#   1 = 先扫 ROI（快、少误检），没找到再整帧兜底（更稳，推荐）
#   0 = 严格只在 ROI 内识别（绝不看框外，但二维码一旦跑出框就找不到）
QR_ROI_FALLBACK_FULL = 0


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
    sensor.set_framesize(sensor.HD)
    sensor.skip_frames(70)
    _sensor_ready = True


def scan_qr_frame():
    """
    单帧扫描二维码。
    返回 (d1, d2, d3) 或 None。
    """
    img = sensor.snapshot()

    # (1) 先只在 ROI 内找：面积小、速度快、背景干扰少
    #     注意：ROI 要【直接传 4 元组】，不能写成 [QR_ROI]（套 list 会报
    #     ValueError: requested length 4 but object has length 1）
    codes = img.find_qrcodes(QR_ROI)

    # (2) 没找到再整帧兜底（QR_ROI_FALLBACK_FULL=0 时跳过，即"严格只认 ROI"）
    if not codes and QR_ROI_FALLBACK_FULL:
        codes = img.find_qrcodes()        # 无参数 = 整帧扫描

    if QR_DRAW_DEBUG:
        img.draw_rectangle(QR_ROI, color=128)                 # 灰框 = 设定的 ROI

    if codes:
        if QR_DRAW_DEBUG:
            img.draw_rectangle(codes[0].rect(), color=255)    # 白框 = 实际识别到的二维码

        payload = codes[0].payload()

        if QR_DRAW_DEBUG:
            print("[QR] ROI=%s payload=%s" % (str(QR_ROI), payload))

        if len(payload) == 3 and payload.isdigit():
            d1 = int(payload[0])
            d2 = int(payload[1])
            d3 = int(payload[2])
            if 1 <= d1 <= 3 and 1 <= d2 <= 3 and 1 <= d3 <= 3:
                return (d1, d2, d3)
    return None
