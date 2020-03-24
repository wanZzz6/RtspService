import cv2
import logging

logger = logging.getLogger('algorithm')

ALGORITHM_DEMO_RTCT = 1
ALGORITHM_DEMO_LINE = 2
ALGORITHM_DEMO_CIRCLE = 3
ALGORITHM_DEMO_ELLIPSE = 4


def draw_rectangle(frame):
    cv2.rectangle(frame, (0, 0), (50, 50), (255, 0, 0), 3)  # 长方形
    return frame


def draw_line(frame):
    cv2.line(frame, (0, 0), (100, 100), (0, 255, 0), 5)  # 直线
    return frame


def draw_circle(frame):
    cv2.rectangle(frame, (0, 0), (50, 50), (0, 0, 255), 3)  # 矩形
    return frame


def draw_ellipse(frame):
    cv2.ellipse(frame, (100, 100), (100, 50), 0, 0, 360, (255, 255, 0), 4)  # 椭圆
    return frame


def draw_nothing(frame):
    return frame


ALGORITHM_MAP = {
    1: draw_rectangle,
    2: draw_rectangle,
    3: draw_circle,
    4: draw_ellipse
}


# todo 算法优先级

def get_algorithm_by_index(index):
    alig = ALGORITHM_MAP.get(index)
    if alig:
        return alig
    else:
        logger.warning('Algorithm not found by index - [{}]'.format(index))
        return draw_nothing
