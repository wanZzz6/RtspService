# -*- coding: utf-8 -*-
from logging_config import getLogger
import traceback

import oss2
from oss2.exceptions import NoSuchKey

from utils import gen_uuid
import logging

logger = getLogger('MyOssClient')
# logger.setLevel('DEBUG')
oss2.set_file_logger('logs/oss.log', 'oss2', logging.INFO)


# 详细通讯日志
# oss2.set_stream_logger()


# todo :oss2.defaults设置Session连接池;
# todo 取消crc 校验

class OssClient(object):
    def __init__(self, access_key_id, access_key_secret, bucket_name, endpoint, *args, **kwargs):
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._bucket_name = bucket_name
        self.endpoint = endpoint
        self._cdn = kwargs.pop('cdn', "")
        self._auth = None
        self._bucket = None
        self.init_bucket()

    def init_bucket(self):
        try:
            self._auth = oss2.Auth(self._access_key_id, self._access_key_secret)
            # 已有session将不会重新创建
            self._bucket = oss2.Bucket(self._auth, self.endpoint, self._bucket_name, connect_timeout=4)
            logger.debug("Init Bucket Success")
        except Exception:
            logger.fatal("Init Bucket Fail!\n{}".format(traceback.format_exc()))
            raise

    # def ensure_init(func):
    #     """装饰器"""
    #
    #     def check_init(self, *args, **kwargs):
    #         if self._bucket is None:
    #             self.init()
    #         return func(self, *args, **kwargs)
    #     return check_init

    def put_object(self, data, key='', headers=None, progress_callback=None):
        """
        上传一个文件对象
        :param key: key, if None, gengrate a uuid.
        :param data: 待上传的内容。
        :type data: bytes，str或file-like object
        :param headers: 用户指定的HTTP头部。可以指定Content-Type、Content-MD5、x-oss-meta-开头的头部等
        :type headers: 可以是dict，建议是oss2.CaseInsensitiveDict

        :param progress_callback: 用户指定的进度回调函数。可以用来实现进度条等功能。参考 :ref:`progress_callback` 。

        :return : Success: cdn url. Fail: None
        """

        if not key:
            key = gen_uuid()
        result = self._bucket.put_object(key, data, headers, progress_callback)

        if result.status == 200:
            logger.debug("Put Success. {}".format(key))
            return self._cdn + key
        else:
            logger.error('Put [{}] result code: {}'.format(key, result.status))

    def put_object_from_file(self, key, filename, headers=None, progress_callback=None) -> bool:
        """
        上传一个本地文件到OSS的普通文件
        :param str key: 上传到OSS的文件名
        :param str filename: 本地文件名，需要有可读权限
        :return : cdn url if success
        """
        result = self._bucket.put_object_from_file(key, filename, headers, progress_callback)

        if result.status == 200:
            logger.debug("Put Success - {}".format(key))
            return self._cdn + key
        else:
            logger.error('put [{}] result code: {}'.format(key, result.status))

    def get_object(self, key):
        """
        下载一个文件。
        :return: file content bytes.
        """
        try:
            result = self._bucket.get_object(key)
            return result.read()
        except NoSuchKey as e:
            logger.error('{0} not found: http_status={1}, request_id={2}'.format(key, e.status, e.request_id))

    def delete_object(self, key) -> bool:
        """
        删除一个文件。
        :return : bool, del success or not`
        """
        result = self._bucket.delete_object(key)

        if result.status == 204:
            logger.debug('del success - {}'.format(key))
            return True
        else:
            logger.error('del {} fail : {}'.format(key, result.status))
            return False

    def object_exists(self, key) -> bool:
        return self._bucket.object_exists(key)

    def __enter__(self):
        self.init_bucket()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __del__(self):
        pass


if __name__ == '__main__':
    from oss.config import oss_config

    my_utils = OssClient(oss_config['accessKeyId'], oss_config['accessKeySecret'], oss_config['bucketName'],
                         oss_config['endpoint'],
                         cdn=oss_config['cdn'])

    key = 'test.txt'
    content = 'Hello World'
    print("上传文件：", my_utils.put_object(content, key))
    print('是否存在；', my_utils.object_exists(key))
    print('读取文件内容: ', my_utils.get_object(key))
    print('删除OK ?：', my_utils.delete_object(key))
