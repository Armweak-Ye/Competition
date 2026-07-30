# 测试救援区形状识别 → 重命名为 main.py 后点开始按钮
# 改 TEST_SHAPE 选择形状: 1=圆柱 2=圆锥 3=腰鼓

import sensor, image, time

TEST_SHAPE = 1  # <<< 改这里选形状

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

names = {1: "圆柱", 2: "圆锥", 3: "腰鼓"}
print("=== 救援区形状识别测试 ===")
print("目标: %s\n" % names[TEST_SHAPE])


def get_width_profile(img, blob):
    N = 7
    profile = []
    for i in range(N):
        y = blob.y() + blob.h() * i // N
        y = min(img.height() - 1, max(0, y))
        cx = blob.cx()
        left, right = blob.x(), blob.x() + blob.w()
        for x in range(cx, left, -1):
            if img.get_pixel(x, y) < 200:
                left = x + 1
                break
        for x in range(cx, right):
            if img.get_pixel(x, y) < 200:
                right = x - 1
                break
        w = right - left
        if w < 0:
            w = 0
        profile.append(w)
    return profile


def classify(profile):
    if len(profile) < 3:
        return 0
    avg = sum(profile) // len(profile)
    var = sum((w - avg) ** 2 for w in profile) / len(profile)
    if var < 50:
        return 1
    dec = all(profile[i] >= profile[i + 1] - 3 for i in range(len(profile) - 1))
    if dec and profile[0] > profile[-1] * 1.3:
        return 2
    mid = len(profile) // 2
    top_avg = sum(profile[:2]) // 2
    bot_avg = sum(profile[-2:]) // 2
    if profile[mid] < top_avg * 0.8 and profile[mid] < bot_avg * 0.8:
        return 3
    return 0


while True:
    img = sensor.snapshot()
    img.lens_corr(1.5)
    blobs = img.find_blobs([(200, 255)], pixels_threshold=200,
                            area_threshold=300, merge=True)
    if blobs:
        for b in sorted(blobs, key=lambda x: x.area(), reverse=True):
            profile = get_width_profile(img, b)
            shape = classify(profile)
            marker = " <== 目标!" if shape == TEST_SHAPE else ""
            print("%s: X=%3d Y=%3d W=%3d H=%3d  profile=%s%s" %
                  (names.get(shape, "未知"), b.cx(), b.cy(), b.w(), b.h(),
                   str(profile), marker))
    else:
        print("未检测到")
    print("---")
    time.sleep_ms(300)
