import threading
import time
from urllib.parse import urlparse

import cv2

from analyse.algorithm import ALGORITHM_MAP
from logging_config import getLogger
import requests
from client import Client

logger = getLogger('test')


def change_ai(url, channel, ai_index):
    data = {
        "channel": channel,
        'ai_index': ai_index
    }
    res = requests.post(url, data=data)
    print(res.status_code, res.json())


def test_trans1(rtsp_url: str, number: int):
    total_post = 25 * 10
    client = Client(rtsp_url, verbose=False)
    error_count = 0
    post_count = 0
    while True:
        if post_count > total_post:
            break
        resp = client.describe()
        if resp.status != 200:
            logger.error('camera {}'.format(number), resp.status)
            error_count += 1

        time.sleep(0.05)
        post_count += 1
    logger.debug(
        'Stream {}, total: {}, fail {}， success {}%,'.format(
            number, total_post, error_count, ((total_post - error_count) / total_post) * 100,
            error_count))


def test_trans2(rtst_url: str, number: int):
    cap = cv2.VideoCapture(rtst_url)
    if not cap.isOpened():
        logger.error("setup falied {}".format(number))
        return
    p = urlparse(rtst_url)
    api_url = "http://{}:8000/api/changeAI".format(p.hostname)
    while (1):
        ret, img = cap.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        cv2.imshow("Image{}".format(number), img)
        kbd = cv2.waitKey(1) & 0xFF
        if kbd == ord('q'):
            break
        elif kbd in ALGORITHM_MAP.keys():
            change_ai(api_url, p.path.strip('/'), kbd)

    cap.release()  # 释放摄像头
    cv2.destroyAllWindows()  # 释放窗口资源


if __name__ == '__main__':

    target_url_pattern = 'rtsp://10.86.23.194:8554/camera%d'

    thread_list = []
    for i in range(16):
        t = threading.Thread(target=test_trans2, args=(target_url_pattern % (i + 1), i + 1))
        # t = threading.Thread(target=test_trans1, args=(target_url % (i + 1), i + 1))
        thread_list.append(t)

    for t in thread_list:
        t.start()

    for t in thread_list:
        t.join()

    print('main end')
