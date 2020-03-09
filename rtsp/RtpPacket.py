from time import time

# from random import randint

HEADER_SIZE = 12


class RtpPacket(object):

    def __init__(self):
        self.__payload = None
        self.header = bytearray(HEADER_SIZE)

        # # Fixed Header
        # self.__version = 2
        # self.__padding = 0
        # self.__extension = 0
        # self.__csrc_count = 0
        # self.__marker = 0
        # self.__payloadType = 96
        # self.__seqNum = randint(10000, 99999)  # 自增
        # self.__timestamp = int(time())
        # self.__ssrc = bytearray()

    def encode(self, *, version, padding, extension, csrc_count, marker, pt, seqnum, ssrc, payload, timestamp=None):
        """Encode the RTP packet with header fields and payload."""
        if timestamp is None:
            timestamp = int(time())

        self.header = bytearray(HEADER_SIZE)
        # --------------
        # TO COMPLETE
        # --------------
        # Fill the header bytearray with RTP header fields

        # RTP-version filed(V), must set to 2
        # padding(P),extension(X),number of contributing sources(CC) and marker(M) fields all set to zero in this lab

        # Because we have no other contributing sources(field CC == 0),the CSRC-field does not exist
        # Thus the length of the packet header is therefore 12 bytes

        # Above all done in ServerWorker.py

        # ...
        # header[] =

        # header[0] = version + padding + extension + cc + seqnum + marker + pt + ssrc
        self.version = version
        self.padding = padding
        self.extension = extension
        self.csrc_count = csrc_count
        self.marker = marker
        self.pt = pt
        self.seqNum = seqnum
        self.timestamp = timestamp
        self.ssrc = ssrc

        # Get the payload
        # ...
        self.payload = payload
        return self.header + self.payload

    def decode(self, byteStream):
        """Decode the RTP packet."""

        # print byteStream[:HEADER_SIZE]
        self.header = bytearray(byteStream[:HEADER_SIZE])  # temporary solved
        self.payload = byteStream[HEADER_SIZE:]

    @property
    def version(self):
        """Return RTP version."""
        return int(self.header[0] >> 6)

    @version.setter
    def version(self, ver):
        self.header[0] = ver << 6

    @property
    def padding(self):
        p = self.header[0] >> 5 & 0x01
        return int(p)

    @padding.setter
    def padding(self, pad):
        self.header[0] = self.header[0] | pad << 5

    @property
    def extension(self):
        x = self.header[0] >> 4 & 0x01
        return x

    @extension.setter
    def extension(self, value):
        self.header[0] = self.header[0] | value << 4

    @property
    def csrc_count(self):
        cc = self.header[0] & 0x0F
        return int(cc)

    @csrc_count.setter
    def csrc_count(self, value):
        self.header[0] = self.header[0] | value

    @property
    def marker(self):
        m = self.header[1] >> 7
        return int(m)

    @marker.setter
    def marker(self, value):
        self.header[1] = self.header[1] | value << 7

    @property
    def pt(self):
        """Return payload type."""
        pt = self.header[1] & 0x7F
        return int(pt)

    @pt.setter
    def pt(self, value):
        self.header[1] = self.header[1] | value

    # todo 位运算
    @property
    def seqNum(self):
        """Return sequence (frame) number."""
        seqNum = self.header[2] << 8 | self.header[3]  # header[2] shift left for 8 bits then does bit or with header[3]
        return int(seqNum)

    @seqNum.setter
    def seqNum(self, value):
        self.header[2] = (value >> 8) & 0xFF
        self.header[3] = value & 0xFF

    # todo 位运算
    @property
    def timestamp(self):
        """Return timestamp."""
        timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        return int(timestamp)

    @timestamp.setter
    def timestamp(self, value):
        # todo 位运算
        self.header[4] = (value >> 24) & 0xFF
        self.header[5] = (value >> 16) & 0xFF
        self.header[6] = (value >> 8) & 0xFF
        self.header[7] = value & 0xFF

    @property
    def ssrc(self):
        timestamp = self.header[8] << 24 | self.header[9] << 16 | self.header[10] << 8 | self.header[11]
        return int(timestamp)

    @ssrc.setter
    def ssrc(self, value):
        self.header[8] = (value >> 24) & 0xFF
        self.header[9] = (value >> 16) & 0xFF
        self.header[10] = (value >> 8) & 0xFF
        self.header[11] = value & 0xFF

    @property
    def payload(self):
        """Return payload."""
        return self.__payload

    @payload.setter
    def payload(self, value):
        self.__payload = value

    def getPacket(self):
        """Return RTP packet."""
        return self.header + self.payload
