import traceback

import cv2
import threading

from analyse.algorithm import draw_nothing
from logging_config import getLogger

logger = getLogger('Feed')
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 450
DEFAULT_FPS = 20
SCHEMES = {"rtsp", "rtmp"}  # 用于识别实时流


class Feed(object):
    def __init__(self, stream_source: (str, int), name=None, algor_handler=None):
        """
        :param stream_source:
        :param algor_handler: 图像处理函数
        """

        self.stream_path = stream_source
        self.name = name
        self.handler = algor_handler
        self._is_opened = False
        self._verbose = False
        self.stream = None

    def __del__(self):
        """Release resource."""
        self.close()

    def set_verbose(self, verbose: bool):
        """print some more log prints for debug purpose"""
        self._verbose = verbose

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if value is None:
            logger.warning("You'd better set a name not None.")
        self._name = value

    @property
    def handler(self):
        return self._handler

    @handler.setter
    def handler(self, value):
        if value is None:
            value = draw_nothing
        if callable(value):
            self._handler = value
            logger.debug("[name: {}] - set a handler - {}".format(self.name, value.__name__))
        else:
            raise TypeError("[name: {}] - Invalid frame handler, need a function object".format(self.name))

    def open(self):
        """open the communication"""
        if not self._is_opened:
            ret = self._do_open()
            if ret:
                self._is_opened = True

    def close(self):
        """close the communication with the slave"""
        if self._is_opened:
            ret = self._do_close()
            if ret:
                self._is_opened = False

    def _do_open(self):
        raise NotImplementedError()

    def _do_close(self):
        raise NotImplementedError()

    def make_null_data(self):
        raise NotImplementedError()

    def detect_h_w_fps(self) -> (int, int, int):
        logger.warning("[name: {}] - Use default height, width and fps.".format(self.name))
        return self.get_default_h_w_fps()

    @staticmethod
    def get_default_h_w_fps() -> (int, int, int):
        return DEFAULT_HEIGHT, DEFAULT_WIDTH, DEFAULT_FPS

    def isOpened(self) -> bool:
        return self._is_opened

    def read_raw(self):
        """
        :return: result and data
        """
        raise NotImplementedError()

    def feed_processed_data(self):
        ret, data = self.read_raw()
        if ret:
            try:
                data = self.handler(data)
                return data
            except:
                logger.error(traceback.format_exc())
        logger.error("[name: {}] Generate a fake data".format(self.name))
        return self.make_null_data()

    # def read_latest(self):
    #     raise NotImplementedError()


class OpenCvFeed(Feed):
    def __init__(self, stream_source, name=None, algor_handler=None):
        super().__init__(stream_source, name, algor_handler)
        self._latest_frame = None
        self._reading = False
        self._frame_receiver = None

    def isStarted(self):
        ok_ = self._is_opened
        if ok_ and self._reading:
            ok_ = self._frame_receiver.is_alive()
        return ok_

    def _do_open(self) -> bool:
        """
        Once you start a capture in opencv, you have to keep reading to get the latest frame.
        :return: Boolean
        """
        try:
            cap = cv2.VideoCapture(self.stream_path)
            if cap.isOpened():
                logger.debug("[name: {}] - Capture opened: - {}".format(self.name, self.stream_path))
                self._is_opened = True
                self.stream = cap
                # direct connected camera needn't.
                if isinstance(self.stream_path, str) and self.stream_path[:4] in SCHEMES:
                    self._reading = True
                    self._start_read_latest()
                    # Wait sub thread read at lease one frame.
                    time.sleep(0.1)

                self.read_raw = self._read_latest_frame if self._reading else cap.read

                logger.debug("[name: {}] - Initialize Succeed.".format(self.name))
                return True
                # self._width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                # self._height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                # self._fps = int(cap.get(cv2.CAP_PROP_FPS))
            else:
                raise Exception("Fail to initialized OpenCV Capture !")
        except:
            logger.critical('%s', traceback.format_exc())

    def _do_close(self) -> bool:
        # stop sub thread and release capture.
        self._stop_read_latest()
        self.stream.release()
        logger.debug("[name: {}] Closed : - {}".format(self.name, self.stream_path))
        return True

    def _start_read_latest(self):
        """start a thread to read frame."""
        self._frame_receiver = threading.Thread(target=self.__recv_frame, daemon=True)
        self._frame_receiver.start()

    def _stop_read_latest(self):
        """Stop keeping reading latest frame."""
        self._reading = False
        if self._frame_receiver.is_alive():
            self._frame_receiver.join()

    def __recv_frame(self):
        """Keep reading latest frame."""
        while self._reading and self._is_opened:
            ok, frame = self.stream.read()
            if not ok:
                logger.error('[name: {}] - Opencv Capture Read Frame fail!'.format(self.name))
                break
            self._latest_frame = frame
        self._reading = False

    def _read_latest_frame(self):
        """Just like `VideoCapture.read()`, if success, you will get the latest frame """
        frame = self._latest_frame
        # todo flush ??
        # self._latest_frame = None
        return frame is not None, frame

    # todo 重试次数
    def detect_h_w_fps(self) -> (int, int, int):
        """
        detect picture's width, height and fps.
        :return: (height, width, fps)
        """
        h, w = DEFAULT_HEIGHT, DEFAULT_WIDTH

        fps = int(self.stream.get(cv2.CAP_PROP_FPS))
        if fps < 0 or fps > 35:
            logger.warning("Unsupported FPS : [{}/s], had changed to {}/s".format(fps, DEFAULT_FPS))
            fps = DEFAULT_FPS

        ret, frame = self.read_raw()
        if ret:
            if self._handler is not None:
                # after processed size
                frame = self._handler(frame)
            h, w = frame.shape[:2]
        else:
            logger.error("Fail to detect frame params.")

        logger.debug('[name: {}] Frame size - [width]: {}, [height]: {}, [Fps]: {}'.format(self.name, h, w, fps))
        return h, w, fps

    # todo
    def make_null_data(self):
        return b'null'

    def read_raw(self):
        pass


if __name__ == '__main__':
    import time
    from analyse.algorithm import draw_circle, draw_ellipse, draw_line

    url = 'rtsp://admin:admin777@10.86.77.14:554/h264/ch1/sub/av_stream'
    cap = OpenCvFeed(url, name=123, algor_handler=draw_line)
    cap.open()

    _, _, fps = cap.detect_h_w_fps()
    while True:
        time.sleep(1 / fps)
        img = cap.feed_processed_data()
        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()  # 释放窗口资源
    cap.close()
