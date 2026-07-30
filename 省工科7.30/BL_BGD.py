import sensor, image, time
from pyb import Pin

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)

sensor.set_auto_gain(False)          # 关闭自动增益
sensor.set_auto_whitebal(False)      # 关闭自动白平衡

p_out = Pin('P6', Pin.OUT_PP)
clock = time.clock()

while(True):
    p_out.high()  # 设置 P6 引脚为高电平  点亮
#   p_out.low()   # 设置 P6 引脚为低电平  熄灭
    clock.tick()
    img = sensor.snapshot()
    print(clock.fps())
