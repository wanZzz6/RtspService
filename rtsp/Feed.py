import random
import traceback
import time
import cv2
import numpy as np
import imutils
import threading

from logging_config import getLogger
from config import FRAME_OUTPUT_WIDTH, FRAME_OUTPUT_HEIGHT, OUTPUT_FPS
from utils import draw_frame
from analyse.algorithm import draw_nothing

logger = getLogger('Feed')

SCHEMES = {"rtsp", "rtmp"}  # 用于识别实时流
_UNKNOWN = "UNKNOWN"


def make_null_data(height, width, dimensions=3):
    try:
        # 浪淘沙
        frame = np.random.randint(0, 255, (height, width, dimensions), np.uint8)
        return frame
    except TypeError as e:
        logger.error("Error to generate a null frame, Please set correct frame size.\n%s", e)


class Feed(object):
    def __init__(self, stream_source: (str, int), name, media_format, algor_handler=None):
        """
        :param stream_source:
        :param media_format: RGB，BGR
        :param algor_handler: 图像处理函数
        """

        self.stream_path = stream_source
        self.name = name
        self._handler = None
        self.handler = algor_handler
        self._is_opened = False
        self._verbose = False
        self.stream = None
        self.media_format = media_format

        self._process_interval_frame = 25  # every x frame to process a frame use algor_handler.
        self.process_flag = True  #
        self.width, self.height, self.fps = _UNKNOWN, _UNKNOWN, _UNKNOWN
        # todo 已知bug，直连camera算法处理计数错误。
        self.frame_counter = 0
        self.marker = []  # draw frame rectangle，circle e.g.

    def __del__(self):
        """Release resource."""
        self.close()

    def set_verbose(self, verbose: bool):
        """print some more log prints for debug purpose"""
        self._verbose = verbose

    def set_interval_frame(self, frame: int):
        if 0 < frame < 100:
            self._process_interval_frame = frame
        else:
            logger.warning("Can't set frame internal: {}".format(frame))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if value is None:
            value = str(random.randint(1, 1000))
            logger.warning("You can't set a None name. Generate a random name: {}".format(value))
        self._name = value

    @property
    def handler(self):
        return self._handler

    @handler.setter
    def handler(self, value):
        if self.handler != value:
            if value is None:
                value = draw_nothing
            if callable(value):
                # todo maybe size changed.
                self._handler = value
                logger.debug("[name: {}] - Set a handler - {}".format(self.name, value.__name__))
            else:
                raise TypeError("[name: {}] - Invalid frame handler, need a function object".format(self.name))

    def open(self):
        """open the communication"""
        if not self._is_opened:
            ret = self._do_open()
            if ret:
                self._is_opened = True
                logger.debug("[name: {}] - Initialize Succeed.".format(self.name))
            else:
                logger.debug("[name: {}] - Initialize Failed.".format(self.name))

    def close(self):
        """close the communication with the slave"""
        if self._is_opened:
            ret = self._do_close()
            if ret:
                self._is_opened = False
                logger.debug("[name: {}] Close Succeed.".format(self.name))
            else:
                logger.debug("[name: {}] Close Failed.".format(self.name))

    def _do_open(self):
        raise NotImplementedError()

    def _do_close(self):
        raise NotImplementedError()

    def detect_h_w_fps(self) -> None:
        # logger.warning("[name: {}] - Use default height, width and fps.".format(self.name))
        # return self.get_default_h_w_fps()
        raise NotImplementedError()

    def set_h_w_fps(self, height: int = None, width: int = None, fps_: int = None):
        if isinstance(height, int):
            self.height = height
        if isinstance(width, int):
            self.width = width
        if isinstance(fps_, int):
            if fps_ < 0 or fps_ > 35:
                logger.warning("Unsupported FPS : [{}/s], had changed to {}/s".format(fps_, OUTPUT_FPS))
                fps_ = OUTPUT_FPS
            self.fps = fps_

        logger.debug(
            '[name: {}] - Set frame size to - [width: {}], [height: {}], [Fps: {}]'.format(self.name, self.height,
                                                                                           self.width, self.fps))

    def get_h_w_fps(self) -> (int, int, int):
        if not self._is_opened:
            self.open()
        return self.height, self.width, self.fps

    @staticmethod
    def get_default_h_w_fps() -> (int, int, int):
        return FRAME_OUTPUT_HEIGHT, FRAME_OUTPUT_WIDTH, OUTPUT_FPS

    def isOpened(self) -> bool:
        return self._is_opened

    def read_raw(self):
        """
        :return: result and data
        """
        raise NotImplementedError()

    def make_null_data(self):
        return make_null_data(self.height, self.width)

    def feed(self) -> np.ndarray:
        """
        :return: after processed frame
        """
        ret, frame = self.read_raw()
        if ret:
            # interval
            if self.process_flag:
                self.process_flag = False
                if self.handler:
                    try:
                        self.marker = self.handler(frame)
                    except:
                        logger.error(traceback.format_exc())

            # if no process or hadler occurred error:
            frame = draw_frame(frame, self.marker)
            frame = imutils.resize(frame, width=self.width, height=self.height)
            return frame
        logger.error("[name: {}] - Generate a fake data".format(self.name))
        return make_null_data(self.height, self.width)

    # def read_latest(self):
    #     raise NotImplementedError()


class OpenCvFeed(Feed):
    def __init__(self, stream_source, name, algor_handler=None):
        super().__init__(stream_source, name, "BGR", algor_handler)
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
                # initialize frame params
                self.detect_h_w_fps()
                return True
            else:
                raise Exception("[name: {}] - Fail to initialized OpenCV Capture !".format(self.name))
        except:
            logger.critical('%s', traceback.format_exc())
            exit(-1)

    def _do_close(self) -> bool:
        # stop sub thread and release capture.
        self._stop_read_latest()
        self.stream.release()
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
        error_count = 0
        while self._reading and self._is_opened:
            self.frame_counter += 1
            if self.frame_counter % self._process_interval_frame == 0:
                self.process_flag = True

            ok, frame = self.stream.read()
            if not ok:
                logger.error('[name: {}] - Opencv Capture Read Frame fail!'.format(self.name))
                error_count += 1
                if error_count > 50:
                    break
            # Maybe set a `None` value
            self._latest_frame = frame
        self._reading = False

    def _read_latest_frame(self):
        """Just like `VideoCapture.read()`, if success, you will get the latest frame """
        frame = self._latest_frame
        # todo flush ??
        # self._latest_frame = None
        return frame is not None, frame

    # todo 重试次数，
    def detect_h_w_fps(self) -> None:
        """
        detect picture's width, height and fps. when change handler, auto call.
        """
        if not self._is_opened:
            self.open()
        h, w = None, None

        fps = int(self.stream.get(cv2.CAP_PROP_FPS))
        ret, frame = self.read_raw()
        if ret:
            # todo handler process??
            # resize
            frame = imutils.resize(frame, width=FRAME_OUTPUT_WIDTH, height=FRAME_OUTPUT_HEIGHT)
            h, w = frame.shape[:2]
        else:
            logger.error("Fail to detect frame params, please retry.")

        self.set_h_w_fps(h, w, fps)

    def read_raw(self):
        pass


if __name__ == '__main__':
    import time
    from analyse.algorithm import draw_circle, draw_ellipse, draw_line, draw_rectangle, draw_nothing

    url = 'rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream'
    cap = OpenCvFeed(url, name=123, algor_handler=draw_nothing)
    cap.open()

    _, _, fps = cap.get_h_w_fps()

    while True:
        time.sleep(1 / fps)
        img = cap.feed()
        cv2.imshow("Image", img)
        kbd = cv2.waitKey(1) & 0xFF
        if kbd == ord('q'):
            break
        elif kbd == ord('1'):
            cap.handler = draw_line
        elif kbd == ord('2'):
            cap.handler = draw_rectangle
        elif kbd == ord('3'):
            cap.handler = draw_circle
        elif kbd == ord('4'):
            cap.handler = draw_ellipse
    cv2.destroyAllWindows()  # 释放窗口资源
    cap.close()
