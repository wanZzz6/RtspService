import json
import logging

"""
Pythonic SDP/SDPPLIN Parser
"""

logger = logging.getLogger('SDP')


# def _parse_sdpplin_line(item):
#     """ Returns a (name,value) tuple when given an Sdpplin attribute
#     e.g. AvgPacketSize:integer;744 => (AvgPacketSize,744)
#     """
#     name, value = item.split(':', 1)
#     if value.find(';') != -1:
#         # type = value.split(';')[0]
#         # value = value[len(type) + 1:]
#         type, sep, value = value.partition(';')
#         if type == 'integer':
#             value = int(value)
#         if type == 'buffer':
#             value = base64.b64decode(value[1:-1])
#         if type == 'string':
#             value = value[1:-1]
#     return name, value


class SdpMediaDesc:
    """ SDP Media Desc """

    def __init__(self, m):
        """
        :param m: start line. m=xxxxxx
        """
        # 媒体类型描述
        self.type, self.port, self.protocol, self.format = m.strip().split(' ')
        # 只关注 a\b 属性
        self.attribute = {}
        # bandwidth
        self.bandwidth = None
        # 其他信息
        self.other_info = {}

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.__dict__)

    __repr__ = __str__


class SdpSessionDesc(object):
    """SDP Session Desc """

    def __init__(self):
        self.version = 0
        self.attribute = {}  # a 属性
        self.o = None
        self.c = None
        self.emil = None
        self.bandwidth = None
        self.url = None
        self.phone = None
        self.information = None
        self.session_name = None
        self.session_desc = None
        self.start_time = None
        self.stop_time = None
        # 其他信息
        self.other_info = {}

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.__dict__)

    __repr__ = __str__


class SdpParser(object):

    def __init__(self, data: str = None):
        """ Parses a full SDP data string.
        Alternatively, send lines to the parseLine method. """
        # 多个媒体描述
        self.media = None  # type List
        # 一个会话描述
        self.session = None  # type SdpSessionDesc
        self._last_desc = None
        if data is not None:
            self.parse(data)

    def parse(self, data: str, verbose=True):
        """
        解析 sdp 字符串到 python对象
        :param data:sdp 字符串
        :param verbose: 是否打印解析结果
        :return:
        """
        # Clear history
        self.media = []
        self.session = SdpSessionDesc()
        self._last_desc = self.session

        for line in data.splitlines():
            try:
                if line:
                    self._parseLine(line)
            except Exception as e:
                logger.error("SDP parse error. %s\n%s" % (line, e))

        if verbose:
            logger.debug("%s\n%s", self.session, self.media)
        return self.session, self.media

    def _parseLine(self, line):
        """ Parses an SDP line. SDP protocol requires lines be parsed in order
        as the m= attribute tells the parser that the following a= values
        describe the last m= """

        type_ = line[0]
        value = line[2:].strip()

        if type_ == 'v':
            self.session.version = int(value)
        elif type_ == 'o':
            self.session.o = value
        elif type_ == 'c':
            self.session.c = value
        elif type_ == 's':  # Session Name
            self.session.session_name = value
        elif type_ == 'i':  # Session Description
            self.session.session_desc = value
        elif type_ == 't':  # Time
            self.session.start_time, self.session.stop_time = [int(t) for t in value.split(' ')]
        elif type_ == "e":  # Email
            self.session.emil = value
        elif type_ == 'u':
            self.session.url = value
        elif type_ == 'p':
            self.session.phone = value
        elif type_ == 'b':
            self._last_desc.bandwidth = value
        elif type_ == 'm':
            # 新的媒体描述开始
            self._last_desc = SdpMediaDesc(value)
            self.media.append(self._last_desc)

        elif type_ == 'a':
            k, sep, v = value.partition(':')
            if sep:
                self._last_desc.attribute[k] = v
        else:
            logger.warning('Unknown SDP Type: %s Value %s', type_, value)
            self._last_desc.other_info[type_] = value

    # todo 构建 sdp 字符串
    def build_self(self):
        pass

    def build_new(self, session_desc, media_desc=None):
        pass

    def save_as_json(self, filename):
        """ save """
        with open(filename, 'w', encoding='utf-8') as f:
            obj = {'session': self.session.__dict__,
                   'media': [m.__dict__ for m in self.media]}
            f.write(json.dumps(obj))

    def loadJson(self, filename):
        """ load """
        try:
            with open(filename, encoding='utf-8') as f:
                obj = json.loads(f.read())
                self.session = obj['session']
                self.media = obj['media']
        except:
            logger.error("Load sdp from file fail! - [%s]", filename)
