#!/usr/bin/env python
# install gir1.2-gst-rtsp-server-1.0 
from threading import Thread
from time import clock
import cv2
import gi
import logging
import traceback

logger = logging.getLogger('gi_camera_server')

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject


def get_rtsp():
    # 'rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream'
    return 'rtmp://58.200.131.2:1935/livetv/hunantv'


class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, rtsp_url=get_rtsp(), **properties):
        super(SensorFactory, self).__init__(**properties)
        cap = cv2.VideoCapture(rtsp_url)
        if cap.isOpened():
            print("Capture opened: {}".format(rtsp_url))
            # self._width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            # self._height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            # self._fps = int(cap.get(cv2.CAP_PROP_FPS))

        self._width = 800
        self._height = 450
        self._fps = 20
        self._format = 'I420'
        self.detect_inteval = 1.5  # 秒
        self.number_frames = 0
        self.duration = 1 / self._fps * Gst.SECOND  # duration of a frame in nanoseconds
        self.launch_string = 'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME ' \
                             'caps=video/x-raw,format=BGR,width={},height={},framerate={}/1 ' \
                             '! videoconvert ! video/x-raw,format={} ' \
                             '! x264enc speed-preset=ultrafast tune=zerolatency ' \
                             '! rtph264pay config-interval=1 name=pay0 pt=96'.format(self._width, self._height,
                                                                                     self._fps, self._format)

    def __del__(self):
        self.cap.release()

    def on_need_data(self, src, lenght):
        ret, frame = self.cap.read()
        if ret:
            # cv2.rectangle(frame, (0, 0), (50, 50), (0, 255, 0), 3)
            data = frame.tostring()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.duration = self.duration
            timestamp = self.number_frames * self.duration
            buf.pts = buf.dts = int(timestamp)
            buf.offset = timestamp
            self.number_frames += 1
            retval = src.emit('push-buffer', buf)
            print('pushed buffer, frame {}, duration {} ns, durations {} s'.format(self.number_frames,
                                                                                   self.duration,
                                                                                   self.duration / Gst.SECOND))
            if retval != Gst.FlowReturn.OK:
                print(retval)

    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)

    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)


class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, **properties):
        super(GstServer, self).__init__(**properties)
        self.factory = SensorFactory()
        self.factory.set_shared(True)
        self.get_mount_points().add_factory("/test", self.factory)
        self.attach(None)


GObject.threads_init()
Gst.init(None)

server = GstServer()

loop = GObject.MainLoop()
loop.run()
