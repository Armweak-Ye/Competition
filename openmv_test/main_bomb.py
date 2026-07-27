# 测试排爆物定位 → 重命名为 main.py 后点开始按钮
# 改 TEST_COLOR 选择颜色: 1=红 2=绿 3=蓝

import sensor, image, time

TEST_COLOR = 1  # <<< 改这里选颜色

THRESHOLDS = {
    1: (0, 45, 40, 80, 20, 80),      # 红
    2: (25, 75, -80, -20, 5, 60),     # 绿
    3: (15, 55, -10, 50, -80, -30),   # 蓝
}

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

names = {1: "红色", 2: "绿色", 3: "蓝色"}
threshold = THRESHOLDS[TEST_COLOR]
print("=== 排爆物定位测试 ===")
print("目标: %s爆炸物\n" % names[TEST_COLOR])

while True:
    img = sensor.snapshot()
    img.lens_corr(1.5)
    blobs = img.find_blobs([threshold], pixels_threshold=80,
                            area_threshold=80, merge=True)
    if blobs:
        # 取圆形度 > 0.4 的最大 blob
        candidates = [b for b in blobs if b.roundness() > 0.4]
        b = max(candidates, key=lambda x: x.area()) if candidates else max(blobs, key=lambda x: x.area())
        print("X=%3d Y=%3d W=%3d H=%3d R=%.2f" %
              (b.cx(), b.cy(), b.w(), b.h(), b.roundness()))
    else:
        print("未检测到")
    time.sleep_ms(300)
