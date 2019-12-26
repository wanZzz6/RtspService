import uuid
import cv2
import logging
import numpy as np

from PIL import Image

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


print(__file__)
