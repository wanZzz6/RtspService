import cv2
from logging_config import getLogger
import threading

logger = getLogger('RTSP_Feed')


class RTSCapture(cv2.VideoCapture):
    """Real Time Streaming Capture.
    这个类必须使用 RTSCapture.create 方法创建，请不要直接实例化
    """

    _cur_frame = None
    _reading = False
    schemes = ["rtsp", "rtmp"]  # 用于识别实时流

    @staticmethod
    def create(url, *schemes):
        """实例化&初始化
        rtscap = RTSCapture.create("rtsp://example.com/live/1")
        or
        rtscap = RTSCapture.create("http://example.com/live/1.m3u8", "http://")
        """
        cap = RTSCapture(url)
        cap.frame_receiver = threading.Thread(target=cap.__recv_frame, daemon=True)
        # 直连设备采集的是实时图像， 不需要一直读取
        if isinstance(url, str) and url[:4] in cap.schemes:
            cap._reading = True

        return cap

    def isStarted(self):
        """替代 VideoCapture.isOpened() """
        ok_ = self.isOpened()
        if ok_ and self._reading:
            ok_ = self.frame_receiver.is_alive()
        return ok_

    def __recv_frame(self):
        """子线程读取最新视频帧方法"""
        while self._reading and self.isOpened():
            ok_, frame_ = self.read()
            if not ok_:
                break
            self._cur_frame = frame_
        self._reading = False

    def read2(self):
        """读取最新视频帧
        返回结果格式与 VideoCapture.read() 一样
        """
        frame = self._cur_frame
        self._cur_frame = None
        return frame is not None, frame

    def start_read(self):
        """启动子线程读取视频帧"""
        self.frame_receiver.start()
        self.read_latest_frame = self.read2 if self._reading else self.read

    def stop_read(self):
        """退出子线程方法"""
        self._reading = False
        if self.frame_receiver.is_alive():
            self.frame_receiver.join()


if __name__ == '__main__':
    rtscap = RTSCapture.create('rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream')
    rtscap.start_read()  # 启动子线程并改变 read_latest_frame 的指向

    while rtscap.isStarted():
        ok, frame = rtscap.read_latest_frame()  # read_latest_frame() 替代 read()
        if not ok:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # 帧处理代码写这里
        cv2.imshow("cam", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    rtscap.stop_read()
    rtscap.release()
    cv2.destroyAllWindows()
