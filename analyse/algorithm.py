import logging

logger = logging.getLogger('algorithm')

ALGORITHM_DEMO_RTCT = 1
ALGORITHM_DEMO_LINE = 2
ALGORITHM_DEMO_CIRCLE = 3
ALGORITHM_DEMO_ELLIPSE = 4


def draw_line(frame):
    # 直线
    marker = [
        {
            'method': 'line',
            'param': [(0, 0), (50, 50), (0, 255, 0), 5],
        }
    ]
    # frame = imutils.resize(frame, width=FRAME_OUTPUT_WIDTH, height=FRAME_OUTPUT_HEIGHT)
    return marker


def draw_rectangle(frame):
    marker = [{
        "method": 'rectangle',
        "param": [(50, 0), (100, 50), (255, 0, 0), 3]
    }]
    return marker


def draw_circle(frame):
    marker = [{
        'method': "circle",
        "param": [(125, 25), 25, (0, 0, 255), 3]
    }]
    return marker


def draw_ellipse(frame):
    # 椭圆
    marker = [
        {
            'method': 'ellipse',
            'param': [(200, 25), (50, 25), 0, 0, 360, (255, 255, 0), 4]
        },
    ]
    return marker


def draw_nothing(frame):
    return []


ALGORITHM_MAP = {
    0: draw_nothing,
    1: draw_rectangle,
    2: draw_line,
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
