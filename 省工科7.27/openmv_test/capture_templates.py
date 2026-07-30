# 模板采集脚本 → 重命名为 main.py 后点开始按钮
# 每 5 秒自动保存一张到 SD 卡 /templates/ 目录

import sensor, image, time

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

count = 0
print("=== 模板采集 ===")
print("每 5 秒保存一张\n")

while True:
    img = sensor.snapshot()
    img.save("capture_%03d.pgm" % count)
    print("已保存: capture_%03d.pgm   (IDE文件浏览器右键下载)" % count)
    count += 1
    time.sleep(5)
