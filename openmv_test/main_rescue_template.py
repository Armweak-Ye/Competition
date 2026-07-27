# main_rescue_template.py — 救援区形状识别（模板匹配版）
# 与 main_rescue.py 功能相同，但改用 NCC 模板匹配替代宽度曲线分析。
#
# 使用前：先运行 capture_templates.py 捕获三个模板（.pgm 文件），
#         将文件放到 OpenMV 内部flash或SD卡，路径填入下方的 TEMPLATE_PATHS。
#
# 注意：
#   NCC 模板匹配对旋转和缩放敏感，模板必须在相同距离和角度下捕获。
#   如果匹配不到，适当降低 MATCH_THRESHOLD。

import sensor
import image
import time

# ==================== 模板文件路径 ====================
# 将模板 .pgm 文件放到 OpenMV 后，修改这里的路径
TEMPLATE_PATHS = {
    1: "cylinder_template.pgm",  # 圆柱
    2: "cone_template.pgm",      # 圆锥
    3: "drum_template.pgm",      # 腰鼓
}

MATCH_THRESHOLD = 0.6  # NCC 匹配阈值，0~1，越低越容易匹配但误检越多

# ==================== 加载模板 ====================
templates = {}
names = {1: "圆柱", 2: "圆锥", 3: "腰鼓"}

print("=== 加载模板 ===")
for shape_id, path in TEMPLATE_PATHS.items():
    try:
        templates[shape_id] = image.Image(path, copy_to_fb=True)
        w = templates[shape_id].width()
        h = templates[shape_id].height()
        print("  已加载: %s (%dx%d) -> %s" % (path, w, h, names[shape_id]))
    except Exception as e:
        print("  加载失败: %s -> %s" % (path, e))

if not templates:
    print("错误：没有成功加载任何模板，请先运行 capture_templates.py")
    raise Exception("No templates loaded")

# ==================== 初始化摄像头 ====================
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(60)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

clock = time.clock()

print("=== 救援区形状识别（模板匹配）===")
print("匹配阈值: %.2f" % MATCH_THRESHOLD)
print("")

while True:
    clock.tick()
    img = sensor.snapshot()
    img.lens_corr(1.5)

    best_shape = 0
    best_score = 0
    best_pos = (0, 0)
    best_template = None

    # 对每个模板做 NCC 匹配，取分数最高的
    for shape_id, template in templates.items():
        matches = img.find_template(template, MATCH_THRESHOLD,
                                     step=4, search=image.SEARCH_EX)

        if matches:
            # matches 是 [(x, y, score), ...] 按分数降序排列
            score = matches[0][2]
            if score > best_score:
                best_score = score
                best_shape = shape_id
                best_pos = (matches[0][0], matches[0][1])
                best_template = template

    # ===== 绘制结果 =====
    fps = clock.fps()
    img.draw_string(0, 0, "FPS:%.1f" % fps, color=127)

    if best_shape > 0:
        tw = best_template.width()
        th = best_template.height()
        cx = best_pos[0] + tw // 2
        cy = best_pos[1] + th // 2

        # 画匹配框
        img.draw_rectangle(best_pos[0], best_pos[1], tw, th, color=127)
        # 画中心十字
        img.draw_cross(cx, cy, color=127, size=10)
        # 画形状名和分数
        label = "%s %.2f" % (names[best_shape], best_score)
        img.draw_string(cx + 10, cy - 6, label, color=127)

        print("[MATCH] %s  中心=(%3d,%3d)  分数=%.2f  FPS=%.1f" %
              (names[best_shape], cx, cy, best_score, fps))
    else:
        print("[MATCH] 未识别  FPS=%.1f" % fps)
