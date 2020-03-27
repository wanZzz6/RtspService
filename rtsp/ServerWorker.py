import socket
import threading
from io import StringIO
from random import randint

from RtpPacket import RtpPacket
from VideoStream import VideoStream
from modules import RTSPRequest
from sdpp import SdpSessionDesc

from logging_config import getLogger

logger = getLogger('ServerWorker')

RTSP_VER = "RTSP/1.0"

OK_200 = 200
Unauthorized = 401
BAD_REQUEST = 400
FILE_NOT_FOUND_404 = 404
CON_ERR_500 = 500

REASON = {
    200: "ok",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error",
    503: "Server Unavailable",
}


class ServerWorker(object):
    INIT = 0
    READY = 1
    PLAYING = 2

    clientInfo = {}

    def __init__(self, clientInfo):
        self.state = self.INIT
        self.stream = None
        self.clientInfo = clientInfo
        # todo xxx
        self.session_desc = SdpSessionDesc()
        self.session_id = None

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)
            if data:
                # todo encode
                data = StringIO(data.decode())
                print("Data received:\n", data)
                self.processRtspRequest(data)

    # todo 装饰器验证
    def _verify_setup(self, req_header):
        """
        verify SETUP request headers
        :param req_header:
        :return:
        """
        # todo xxx
        # Get the RTP/UDP port from the last line
        transport = req_header.get('transport')

        if transport:
            trans_type, cast, info = transport.split(';')
            if trans_type.strip() != 'RTP/AVP/TCP':
                logger.error('Unsupported stream %s' % trans_type)
                return BAD_REQUEST
            # todo xxx
            # elif trans_type.strip() == 'RTP/AVP/UDP':
            #     self.clientInfo['rtpPort'] =
        else:
            logger.warning('Transport Headers Not Found!')
            return BAD_REQUEST

        return OK_200

    def _open_stream(self, stream_source):
        # if self.stream and (self.stream.filename != stream_source):
        #     # close former
        #     if not self.stream.closed:
        #         logger.debug('shutdown {}'.format(self.stream.filename))
        #         self.stream.close()
        # logger.debug('Setup a new stream - {}'.format(stream_source))
        # 准备数据流
        try:
            self.stream = VideoStream(stream_source)
        except:
            logger.error("setup stream fail - [{}]".format(stream_source))
            return False
        else:
            # Update state
            self.state = self.READY
            # Generate a randomized RTSP session ID
            self.session_id = randint(100000, 999999)
        return True

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""

        requ = RTSPRequest(data)
        requestType = requ.method
        seq = requ.headers.get('CSeq')

        replay_code = OK_200
        info = None
        body = None

        # todo 认证
        if requestType == 'SETUP':
            logger.debug("processing SETUP\n")
            replay_code = self._verify_setup(requ.headers)
            # 验证通过
            if replay_code == OK_200:
                stream_source = requ.path
                # 初始建立或者建立新的
                if self.state == self.INIT:
                    self._open_stream(stream_source)
                # Already setup.
                elif self.state:
                    # setup a new stream
                    if self.stream.filename != stream_source:

                        self.stream = VideoStream(stream_source)
                    else:
                        logger.debug('Already setup % - {}'.format(stream_source))

        elif requestType == "PLAY":
            if self.state == self.READY:
                print("processing PLAY\n")

                self.state = self.PLAYING

                self.clientInfo["rtpSocket"] = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM)
                self.clientInfo['event'] = threading.Event()

                self.replyRtsp(OK_200, seq[1])

                threading.Thread(target=self.recvRtspRequest).start()

        # Process PAUSE request
        # ...
        elif requestType == 'PAUSE':
            if self.state == self.PLAYING:
                print("processing PAUSE\n")

                self.state = self.READY

                self.clientInfo['event'].set()

                self.replyRtsp(OK_200, seq[1])

        # Process TEARDOWN request
        elif requestType == 'TEARDOWN':
            logger.debug("processing TEARDOWN\n")

            self.clientInfo['event'].set()

            self.replyRtsp(OK_200, seq[1])

            self.clientInfo['rtpSocket'].close()

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(
                        self.makeRtp(data, frameNumber), (address, port))
                except:
                    print("Connection Error")

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        # -------------
        # TO COMPLETE
        # -------------
        # Set the fields
        # ...
        V = 2
        P = 0
        X = 0
        CC = 0
        M = 0
        PT = 26
        seqNum = frameNbr
        SSRC = 0

        # Create and encode the RTP packet
        # ...
        rtpPacket = RtpPacket()
        rtpPacket.encode(V, P, X, CC, seqNum, M, PT, SSRC, payload)

        # Return the RTP packet
        # ...
        return rtpPacket.getPacket()

    def replyRtsp(self, code: int, seq: (int, str), body: str = None, *args):
        """Send RTSP reply to the client.
        :param body: response content (e.g. sdp)
        :param session: need session id ?
        :param code: status code
        :param seq: CSeq
        :param args: other important info according to method.
        """
        reply = [
            '{} {} {}'.format(RTSP_VER, code, REASON[code]),
            'CSeq: {}'.format(seq),
            *args,
        ]

        if code == OK_200:
            session_header = 'Session: {}'.format(self.clientInfo.get('session'))
            reply.append(session_header)
        else:
            # Error Message
            logger.error("{} - {}".format(code, REASON[code]))

        if body:
            try:
                body_length = len(body)
                reply.append("Content-Length: {}".format(body_length))
                # headers end
                reply.append('')
                reply.append(body)
            except TypeError:
                logger.error('Invalid response content - {}'.format(body))
        else:
            reply.append('\r\n')

        reply = '\r\n'.join(reply)
        connSocket = self.clientInfo['rtspSocket'][0]
        connSocket.send(reply.encode())
