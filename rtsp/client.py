"""
    RTSP/2.0 Protocol
    spec: https://tools.ietf.org/html/rfc7826

Overview:
    1. Session establishment
        1. setup
            1. socket connection
            2. authentication
        2. presentation description
            1. determine media streams are available
            2. determine media delivery protocol used (media initialization)
            3. determine resource identifiers of the media streams
            4. establish session with specific resources and media
    2. Media Delivery Control
        1. Transmission Control
        2. Synchronization
        3. Termination
"""
import re
import socket
from enum import Enum
from io import StringIO
from urllib.parse import urlparse

from auth import digest
from modules import RTSPException
from modules import RTSPResponse
from sdpp import SdpParser

##########################################################
#################   Protocol Constants   #################
##########################################################

HEADER_SIZE = 12
RTSP_VER = "RTSP/1.0"
USER_AGENT = 'py-rtsp'
TRANSPORT = "HTTP"
DEFAULT_PORT = 554

states = Enum('state', "init ready play")
requests = Enum('requests', "options describe setup play pause teardown")
SESSION_PATTERN = r'\s*(?P<session_id>\d+)(.*timeout=)?(?P<timeout>\d+)?'


##########################################################
#################   Default Server URI   #################
##########################################################
def _cam_uri():
    return "rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream"


def printrec(recst: bytes):
    """
    Pretty-printing rtsp strings
    :param recst:
    :return:
    """

    try:
        recst = recst.decode('UTF-8')
    except AttributeError:
        pass
    for x in recst.splitlines():
        if x:
            print("    " + x)
    print()


##########################################################
#################          API           #################
##########################################################
class Client:
    """ RTSP requests which serialize to bytestrings for transmission """

    @property
    def server(self):
        return self._server

    @property
    def serverbase(self):
        return "{}://{}".format(self.server.scheme, self.server.hostname)

    @property
    def media(self):
        return "{}://{}{}".format(self.server.scheme, self.server.hostname, self.server.path)

    def __init__(self, server_uri=_cam_uri(), verbose=True):
        self.verbose = verbose
        self._server = urlparse(server_uri)

        # user_info, have_info, _ = self._server.netloc.rpartition('@')
        # if have_info:
        #     username, have_password, password = user_info.partition(':')
        #     if not have_password:
        #         password = None
        # else:
        #     username = password = None
        # self.username = username
        # self.password = password

        if not self.server.port:
            self._server = self.server._replace(netloc="{}:{}".format(self.server.netloc, DEFAULT_PORT))

        self.state = states.init
        self.rtsp_seq = 0

        self.need_auth = False  # 该连接是否需要认证
        self.session_id = None  # 会话id
        self.session_desc = None  # sdp 会话描述
        self.media_desc = None  # sdp 媒体描述
        self.stream_path = None  # 播放源

        self._auth_info = {
            # todo 只支持单向 摘要认证
            'auth_method': 'Digest',  # 默认摘要认证方式
            'username': self.server.username,
            'realm': None,
            'password': self.server.password,
            'method': None,
            # todo 地址是否会变
            'uri': self.media,
            'nonce': None,
            'qop': None,
            'response': None
        }

        self._connect()

    def __enter__(self, *args, **kwargs):
        """ Returns the object which later will have __exit__ called.
            This relationship creates a context manager. """
        return self

    def __exit__(self, type_=None, value=None, traceback=None):
        """ Together with __enter__, allows support for with- clauses. """
        if self.sock:
            self.sock.__exit__()
            print('Socket disconnected')

    def __del__(self):
        self.__exit__()

    # todo 异步
    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect((self.server.hostname, self.server.port))
        if self.verbose:
            print("Socket connected to \'{}:{}\'.".format(self.server.hostname, self.server.port))

    def _make_auth_str(self):
        """
        拼接请求头的 Authorization字段
        :return: str
        """
        if not self.need_auth:
            return ''
        self._auth_info['response'] = digest(**self._auth_info)
        result = []
        for k, v in self._auth_info.items():
            if v is not None and k not in {'stale', 'password', 'auth_method', 'method'}:
                result.append(k + '="' + v + '"')
        result = 'Authorization: ' + self._auth_info['auth_method'] + ' ' + ', '.join(result) + '\r\n'

        return result

    # todo ''
    def _launch_auth(self, authorization):
        """
        发起认证
        :return: RTSPResponse()
        """
        # 解析响应头字段：Authorization, 获取验证参数
        self._auth_info['auth_method'], info = authorization.strip().split(maxsplit=1)
        d = {}
        for i in re.split(r',\s?', info):
            temp = i.split('=')
            d[temp[0]] = temp[1].replace('"', '')
        # 将参数保存到属性中
        self._auth_info.update(d)
        if d.get('stale').lower() != 'false':
            raise RTSPException('会话过期')

        # todo 重新请求
        return self.__getattribute__(self._auth_info['method'].lower())()

    def _build_response(self, response: str):
        """
        构建rtsp响应对象
        :return: RTSPResponse()
        """
        response = StringIO(response)
        resp = RTSPResponse(response)
        if resp.status == 401:
            # 需要验证
            print(401, resp.reason)
            self.need_auth = True
            authorization = resp.headers.get('WWW-Authenticate')
            resp = self._launch_auth(authorization)

        # response = response.splitlines()
        # resp.version, resp.status_code, resp.reason = response[0].split()
        # resp.headers = {y[0]: y[1].strip() for y in [x.split(':', maxsplit=1) for x in response[1:]] if len(y) > 1}
        return resp

    # todo 异步
    def sendMessage(self, message, reply_len=2048):
        if self.verbose:
            print("Sending message to server:")
            printrec(message)

        if isinstance(message, str):
            message = message.encode('utf-8')
        self.sock.send(message)
        reply = self.sock.recv(reply_len)

        if self.verbose:
            if reply:
                print("Received reply:")
                printrec(reply)
            else:
                raise RTSPException('no reply')
        return self._build_response(reply.decode('UTF-8'))

    def options(self):
        self.rtsp_seq += 1
        self._auth_info['method'] = 'OPTIONS'
        self._auth_info['uri'] = self.media

        request = [
            "OPTIONS {} {}\r\n".format(self.media, RTSP_VER),
            "CSeq: {}\r\n".format(self.rtsp_seq),
            self._make_auth_str(),
            "User-Agent: {}\r\n\r\n".format(USER_AGENT)
        ]
        request = ''.join(request)
        response = self.sendMessage(request.encode('UTF-8'))

        return response

    def describe(self):
        self._auth_info['method'] = 'DESCRIBE'
        self.rtsp_seq += 1
        self._auth_info['uri'] = self.media

        request = [
            "DESCRIBE {} {}\r\n".format(self.media, RTSP_VER),
            "CSeq: {}\r\n".format(self.rtsp_seq),
            # 认证字段
            self._make_auth_str(),
            "User-Agent: {}\r\n".format(USER_AGENT),
            "Accept: application/sdp\r\n\r\n"
        ]
        request = ''.join(request)
        response = self.sendMessage(request.encode('UTF-8'))
        # 解析sdp
        if response.status == 200:
            self._parse_sdp(response.content)

        return response

    def _parse_sdp(self, sdp_content):
        parser = SdpParser()
        self.session_desc, media_desc = parser.parse(sdp_content)
        for media in media_desc:
            # 只关注视频流
            if media.type.lower() == 'video':
                self.media_desc = media
                self.stream_path = media.attribute['control']
                break
            else:
                printrec(b'No play stream')

    def setup(self):
        """ SETUP method defined by RTSP Protocol - https://tools.ietf.org/html/rfc7826#section-13.3 """
        self.rtsp_seq += 1
        self._auth_info['method'] = 'SETUP'
        self._auth_info['uri'] = self.stream_path

        ## example: SETUP rtsp://example.com/foo/bar/baz.rm RTSP/2.0
        request = [
            "SETUP {} {}\r\n".format(self.stream_path, RTSP_VER),
            "CSeq: {}\r\n".format(self.rtsp_seq),
            # todo TCP
            "Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n",
            # RTP/SAVPF,RTP/AVP;unicast;client_port=5000-5001,RTP/AVP/UDP;unicast;client_port=5000-5001\r\n"
            "User-Agent: {}\r\n\r\n".format(USER_AGENT),
            self._make_auth_str(),
        ]
        request = ''.join(request)
        response = self.sendMessage(request.encode('UTF-8'))

        if response.status == 200:
            session_id = response.headers.get('session')
            a = re.match(SESSION_PATTERN, session_id)
            self.session_id = a.group('session_id')
            # timeout = a.group('timeout')
            # todo timeout
        return response

    def pause(self):
        self.rtsp_seq += 1
        self._auth_info['method'] = 'PAUSE'

        request = "PAUSE rtsp://{}{} {}\r\n".format(self.server, self.stream_path, RTSP_VER)
        request += "CSeq: {}\r\n".format(self.rtsp_seq)
        request += "Session: {}\r\n\r\n".format(self.session_id)

        return self.sendMessage(request.encode('UTF-8'))

    def get_session(self):
        self.rtsp_seq += 1

        request = "GET_PARAMETER SESSION\r\n"
        request += "CSeq: {}\r\n\r\n".format(self.rtsp_seq)

        response = self.sendMessage(request.encode('UTF-8'))
        return response

    def get_parameter(self, parameter):
        self.rtsp_seq += 1
        request = "GET_PARAMETER {}\r\n".format(parameter)
        request += "CSeq: {}\r\n".format(self.rtsp_seq)
        request += "Session: {}\r\n".format(self.session_id)
        request += "Content-Type: text/parameters\r\n"
        request += "Content-Length: 15\r\n\r\n"
        # request+= "Transport\r\n\r\n"
        # request+= "jitter\r\n"

        response = self.sendMessage(request.encode('UTF-8'))
        return response


def get_resources(client):
    """ Do an RTSP-DESCRIBE request, then parse out available resources from the response """
    resp = client.options()
    # resp = client.describe().split('\r\n')
    # resources = [x.replace('a=control:','') for x in resp if (x.find('control:') != -1 and x[-1] != '*' )]
    # return resources


if __name__ == '__main__':
    client = Client()
    client.describe()
    client.options()
    client.describe()
    response = client.setup()
    print(response.headers.items())
    print(client.session_desc)
    printrec(client.stream_path)
