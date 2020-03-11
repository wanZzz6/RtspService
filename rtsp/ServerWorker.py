import socket
import threading
from io import StringIO
from random import randint

from RtpPacket import RtpPacket
from VideoStream import VideoStream
from modules import RTSPRequest

import logging_config, logging

logging_config.initLogConf()
logger = logging.getLogger('ServerWorker')

RTSP_VER = "RTSP/1.0"

OK_200 = 200
FILE_NOT_FOUND_404 = 404
CON_ERR_500 = 500
Unauthorized = 401

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
        self.clientInfo = clientInfo
        self.state = self.INIT

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

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""

        requ = RTSPRequest(data)
        requestType = requ.method
        seq = requ.headers.get('CSeq')

        replay_code = CON_ERR_500

        # Process SETUP request
        # todo 认证
        if requestType == 'SETUP':
            video_source = requ.path
            if self.state == self.INIT:
                # Update state
                logger.debug("processing SETUP\n")
                try:
                    # todo 流输入
                    self.clientInfo['videoStream'] = VideoStream(video_source)
                    self.state = self.READY
                    # Generate a randomized RTSP session ID
                    self.clientInfo['session'] = randint(100000, 999999)
                except IOError:
                    replay_code = FILE_NOT_FOUND_404

                # todo xxx
                # Get the RTP/UDP port from the last line
                transport = requ.headers.get('transport')
                if transport:
                    trans_type, cast, info = transport.split(';')
                    if trans_type.strip() != 'RTP/AVP/TCP':
                        logger.error('Unsupported stream %s' % trans_type)
                        replay_code = CON_ERR_500

                    # todo xxx
                    # if trans_type.strip() == 'RTP/AVP/UDP':
                    #     self.clientInfo['rtpPort'] =
                else:
                    logger.error('Transport Headers Not Found!')
                    self.replyRtsp(CON_ERR_500, seq)

                # Send RTSP reply
                self.replyRtsp(OK_200, seq)
            else:
                video_source_f = self.clientInfo.get('videoStream')
                # setup a new stream
                if video_source_f != video_source:
                    logger.debug('shutdown %s' % video_source_f)
                    self.clientInfo['videoStream'].close()
                    self.clientInfo['videoStream'] = VideoStream(video_source)
                    self.clientInfo['session'] = randint(100000, 999999)


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
