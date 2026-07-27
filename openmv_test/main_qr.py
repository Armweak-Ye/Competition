# 测试 QR 扫描 → 重命名为 main.py 后点开始按钮
import sensor, image, time

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.skip_frames(70)

print("=== QR 扫描测试 ===")
print("等待二维码...")

while True:
    img = sensor.snapshot()
    codes = img.find_qrcodes()
    if codes:
        info = codes[0].payload()
        print(info)
    time.sleep_ms(100)
