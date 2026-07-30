# 测试靶标定位 → 重命名为 main.py 后点开始按钮
# 改 TEST_COLOR 选择颜色: 1=红 2=绿 3=蓝

import sensor, image, time

TEST_COLOR = 1  # <<< 改这里选颜色

THRESHOLDS = {
    1: (0, 45, 40, 80, 20, 80),
    2: (25, 75, -80, -20, 5, 60),
    3: (15, 55, -10, 50, -80, -30),
}

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

names = {1: "红色", 2: "绿色", 3: "蓝色"}
threshold = THRESHOLDS[TEST_COLOR]
print("=== 靶标定位测试 ===")
print("目标: %s靶标\n" % names[TEST_COLOR])

while True:
    img = sensor.snapshot()
    img.lens_corr(1.5)
    blobs = img.find_blobs([threshold], pixels_threshold=200,
                            area_threshold=200, merge=True)
    if blobs:
        b = max(blobs, key=lambda x: x.area())
        # 圆检测
        x1 = max(0, b.x() - 20)
        y1 = max(0, b.y() - 20)
        x2 = min(320, b.x() + b.w() + 20)
        y2 = min(240, b.y() + b.h() + 20)
        circles = img.find_circles(threshold=3000, x_margin=10, y_margin=10,
                                    r_margin=10, r_min=3, r_max=80,
                                    roi=(x1, y1, x2 - x1, y2 - y1))
        if circles:
            cx = sum(c.x() for c in circles) // len(circles)
            cy = sum(c.y() for c in circles) // len(circles)
            print("圆心: X=%3d Y=%3d  检测到%d个环  色块: W=%3d" %
                  (cx, cy, len(circles), b.w()))
        else:
            print("色块: X=%3d Y=%3d W=%3d (无圆)" %
                  (b.cx(), b.cy(), b.w()))
    else:
        print("未检测到")
    time.sleep_ms(300)
