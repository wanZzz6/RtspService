import json
import logging

from django.http import HttpResponse
from django.shortcuts import render

from oss.api import OssClient
from oss.config import oss_config
from rtsp.capture_handler import CvCapture

logger = logging.getLogger('RtspService.views')
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
