from django.shortcuts import render
from django.http import HttpResponse
import json
import logging

from oss.api import ossClient
from oss.config import oss_config

oss_client = ossClient(oss_config['access_key_id'], oss_config['access_key_secret'],
                       oss_config['bucket_name'], oss_config['endpoint'])

logger = logging.getLogger(__file__)


# Create your views here.
def home(request):
    return render(request, 'index.html')


def clip(request):
    if request.method == 'POST':
        rtsp = request.POST.get('rtsp')
        key = request.POST.get('key')
        logger.debug(rtsp)
        oss_client.put_object(key, )
    return HttpResponse(json.dumps({'result': 'OK'}), content_type='application/json')
