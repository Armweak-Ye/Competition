# calibrate.py — 测距常数 K 标定
# 赛前在 OpenMV IDE 中单独运行，将输出的 K 值填入 bomb.py 的 K_BOMB
#
# 使用方法：
#   1. 将红色爆炸物放在摄像头正前方 20cm 处
#   2. 在 IDE 中运行此脚本
#   3. 将终端输出的 K 值填入 bomb.py

import sensor
import image
import time

RED_THRESHOLD = (0, 45, 40, 80, 20, 80)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor. VGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

print("将红色爆炸物放在正前方 20cm 处")
time.sleep(2)

while True:
    img = sensor.snapshot()
    blobs = img.find_blobs([RED_THRESHOLD], pixels_threshold=80, area_threshold=80)
    if blobs:
        b = max(blobs, key=lambda x: x.area())
        K = 20 * b.w()
        print("宽度=%d px  →  K=%d" % (b.w(), K))
    else:
        print("未检测到")
    time.sleep_ms(500)
