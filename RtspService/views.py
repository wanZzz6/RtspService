import json
import threading
import time
from django.http import HttpResponse
from django.shortcuts import render

from logging_config import getLogger
from oss.api import OssClient
from oss.config import oss_config
from rtsp.PushServer import FeedMap
from rtsp.capture_handler import CvCapture
from analyse.algorithm import get_algorithm_by_index
from rtsp.PushServer import setup_server

logger = getLogger('RtspService.views')
# OSS客户端
oss_client = OssClient(oss_config['accessKeyId'], oss_config['accessKeySecret'],
                       oss_config['bucketName'], oss_config['endpoint'], cdn=oss_config['cdn'])
# 截图方法
capture_handler = CvCapture()


# Create your views here.
def home(request):
    return render(request, 'index.html')


def capture_service(request):
    result = {}
    try:
        rtsp = request.GET['rtsp']
        key = request.GET['key']
        binary_data = capture_handler.capture_from_rtsp(rtsp)
        access_url = oss_client.put_object(binary_data, key)
        result['status'] = 'ok'
        result['cdn'] = access_url
    except Exception as e:
        logger.error(e)
        result['status'] = 'no'
        result['msg'] = 'see log'
    return HttpResponse(json.dumps(result), content_type='application/json')


def change_ai(request):
    info = {'msg': 'no'}
    if request.method == 'POST':
        channel = request.POST['channel']
        algori_number = int(request.POST['ai_index'])
        logger.debug("%s - %s", channel, algori_number)
        feed = FeedMap.get(channel)
        if feed:
            handler = get_algorithm_by_index(algori_number)
            if handler:
                feed.handler = handler
                info['msg'] = 'ok'
    return HttpResponse(json.dumps(info), content_type='application/json')


def setupServer(request):
    t = threading.Thread(target=setup_server)
    t.setDaemon(True)
    t.start()
    logger.debug(FeedMap)
    return HttpResponse(json.dumps({'msg': 'ok'}), content_type='application/json')
