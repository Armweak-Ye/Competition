import sensor#引入感光元件的模块

# 设置摄像头
sensor.reset()#初始化感光元件
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)#设置图像的大小
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.skip_frames()#跳过n张照片，在更改设置后，跳过一些帧，等待感光元件变稳定。

ROI_X, ROI_Y, ROI_W, ROI_H = 110, 70, 100, 100
ROI = (ROI_X, ROI_Y, ROI_W, ROI_H)

# 一直拍照
while(True):
    img = sensor.snapshot()#拍摄一张照片，img为一个image对象

