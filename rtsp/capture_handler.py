# -*- coding: utf-8 -*-
import logging
import traceback

import cv2

from utils import array2bytes, calc_run_time

logger = logging.getLogger('captureHandler')


class CvCapture(object):
    def __init__(self):
        # todo 缓存rtsp capture 对象
        self.capture_map = dict()
        self.oss_client = None

    # todo 检查cap 队列
    # todo 释放 cap
    @calc_run_time
    def capture_from_rtsp(self, rtsp_url):
        """
        从 rtsp 地址中截图
        :return: success: binary picture; fail: None
        """
        try:
            cap = self.capture_map.get(rtsp_url, None)
            if cap is None:
                cap = cv2.VideoCapture(rtsp_url)  # 子码流平均耗时1~2s，主码流 > 3s, 有可能连接超时
                self.capture_map[rtsp_url] = cap
                logger.debug('Create VideoCapture Success. - {}'.format(rtsp_url))
            return self.capture_from_capture(cap)
        except Exception as e:
            logger.error('Capture Frame Fail!\n {}'.format(traceback.format_exc()))

    @staticmethod
    def capture_from_capture(cap):
        """
        利用已有 capture 对象截图
        :param cap:
        :return: success: binary picture; fail: None
        """
        # if not isinstance(cap, cv2.VideoCapture):
        #     raise TypeError
        try:
            ret, img = cap.read()
            if not ret:
                logging.error("Can't receive frame.")
            else:
                img_bytes = array2bytes(img)
                return img_bytes
        except AttributeError:
            logger.error('capture_from_capture() Need a `cv2.VideoCapture` object\n{}'.format(traceback.format_exc()))
        except Exception:
            logger.error('capture_from_capture Fail!\n{}'.format(traceback.format_exc()))


class FfmpegCapture(object):
    def __init__(self):
        self.ffmpeg = __import__('ffmpeg')

    @calc_run_time
    def capture_from_rtsp(self, rtsp_url):
        """
        利用 ffmpeg 从 rtsp 地址中截图
        :param rtsp_url:
        :return: success: binary picture; fail: None
        """
        out, _ = (
            self.ffmpeg
                .input(rtsp_url)
                .filter('select', 'gte(n,{})'.format(0))
                .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
                .run(capture_stdout=True)
        )
        return out


if __name__ == '__main__':
    url = 'rtmp://58.200.131.2:1935/livetv/hunantv'
    clip = CvCapture()
    with open('test1.jpg', 'wb') as f:
        f.write(clip.capture_from_rtsp(url))
    print('=' * 50)
    with open('test2.jpg', 'wb') as f:
        f.write(FfmpegCapture().capture_from_rtsp(url))
