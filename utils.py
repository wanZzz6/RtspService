import logging
import time
import traceback
import uuid

import cv2

from logging_config import initLogConf

initLogConf()
logger = logging.getLogger('RtspService.utils')


def array2bytes(ndarray_frame, extension='.jpg') -> bytes:
    """
    三维 numpy 数组图片转为二进制 bytes
    :param ndarray_frame: 三维 numpy 数组
    :param extension: 保存图片扩展名
    :return: 图像bytes流
    """

    ret, buf = cv2.imencode(extension, ndarray_frame)
    if ret:
        return buf.tobytes()
    else:
        logger.error("Convert array to bytes fail.")
        return b''


def gen_uuid():
    uuid_4 = uuid.uuid4()
    return uuid_4.hex


def calc_run_time(func):
    """
    Calculate the running time of the function
    :param func: the function need to been calculated
    :return:
    """

    def call_fun(*args, **kwargs):
        start_time = time.time()
        f = func(*args, **kwargs)
        end_time = time.time()
        logger.debug('{0}() run time：{1}'.format(func.__name__, (end_time - start_time)))
        return f

    return call_fun


#
# def resize_frame(height=FRAME_OUTPUT_HEIGHT, width=FRAME_OUTPUT_WIDTH):
#     def decorator(func):
#         def wrapper(frame):
#             frame = imutils.resize(frame, width=width, height=height)
#             return func(frame)
#
#         return wrapper
#
#     return decorator


DRAWER_MAP = {
    "rectangle": cv2.rectangle,
    "line": cv2.line,
    "circle": cv2.circle,
    "ellipse": cv2.ellipse
}


def draw_frame(frame, marker):
    try:
        for item in marker:
            DRAWER_MAP[item['method']](frame, *item['param'])
        return frame
    except:
        logger.error("Draw marker failed %s", traceback.format_exc())
