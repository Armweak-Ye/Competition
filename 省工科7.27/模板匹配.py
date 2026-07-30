# 模板匹配测试 — ROI 对齐工具

import time, sensor, image
from image import SEARCH_EX, SEARCH_DS

sensor.reset()
sensor.set_contrast(1)
sensor.set_gainceiling(16)
sensor.set_framesize(sensor.QVGA)
sensor.set_pixformat(sensor.GRAYSCALE)

template = image.Image("02.pgm")

# 搜索区域 — 调整这四个值来改变 ROI
ROI_X, ROI_Y, ROI_W, ROI_H = 85, 45, 150, 150
ROI = (ROI_X, ROI_Y, ROI_W, ROI_H)

clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    # 画 ROI 参考框 + 十字线，方便对齐目标
    img.draw_rectangle(ROI, color=127)
    img.draw_cross(ROI_X + ROI_W // 2, ROI_Y + ROI_H // 2, color=127)
    img.draw_string(ROI_X + 2, ROI_Y + 2, "ROI", color=127)

    r = img.find_template(template, 0.92, step=4, search=SEARCH_EX, roi=ROI)

    if r:
        img.draw_rectangle(r)

    print(clock.fps())
