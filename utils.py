import logging
import time
import uuid

import cv2
import numpy as np
from PIL import Image
from logging_config import initLogConf

initLogConf()
logger = logging.getLogger('RtspService.utils')


def array2bytes(ndarray_frame, extension='.jpg'):
    """
    np 数组图片转为二进制 bytes
    :return:
    """
    ret, buf = cv2.imencode(extension, ndarray_frame)
    if ret:
        img_bin = Image.fromarray(np.uint8(buf)).tobytes()
        return img_bin
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
