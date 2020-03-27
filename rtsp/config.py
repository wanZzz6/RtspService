# 原图像按等比例缩放后的像素宽度。
FRAME_OUTPUT_WIDTH = 800

# 原图像按等比例缩放后的像素高度，`FRAME_DEFAULT_WIDTH`不为`None`时，此设置无效
FRAME_OUTPUT_HEIGHT = 450

# RTSP推流帧率
OUTPUT_FPS = 20

# RTSP 推流端口
RTSP_SERVER_PORT = 8554

# 推流子信道格式
OUTPUT_SUB_CHANNEL_PATTERN = 'camera%d'

SOURCE_LIST = [
    'rtsp://admin:admin@10.86.77.12:554/h264/ch1/sub/av_stream',
    'rtsp://admin:admin@10.86.77.13:554/h264/ch1/sub/av_stream',

]

