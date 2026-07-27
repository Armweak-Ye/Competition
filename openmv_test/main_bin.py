# 测试排爆桶定位 → 重命名为 main.py 后点开始按钮

import sensor, image, time

BLACK_THRESHOLD = (0, 60, -128, 127, -128, -20)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

print("=== 排爆桶定位测试 ===\n")

while True:
    img = sensor.snapshot()
    img.lens_corr(1.5)
    blobs = img.find_blobs([BLACK_THRESHOLD], pixels_threshold=300,
                            area_threshold=400, merge=True)
    if blobs:
        b = max(blobs, key=lambda x: x.cy() + x.h())
        print("排爆桶: X=%3d Y=%3d W=%3d H=%3d" %
              (b.cx(), b.cy(), b.w(), b.h()))
    else:
        print("未检测到")
    time.sleep_ms(300)
