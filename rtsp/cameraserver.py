#!/usr/bin/env python
# install gir1.2-gst-rtsp-server-1.0

from threading import Thread
import cv2
import gi
from logging_config import getLogger
import traceback

logger = getLogger('gi_camera_server')

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject


def get_rtsp():
    return 'rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream'
    # return 'rtmp://58.200.131.2:1935/livetv/hunantv'


DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 450
DEFAULT_FPS = 20


class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, feed, **properties):
        super(SensorFactory, self).__init__(**properties)

        self._height, self._width, self._fps = feed._detect_h_w_fps()
        print(self._height, self._width, self._fps)

        self._format = 'I420'
        self.detect_inteval = 1.5  # 算法执行间隔， 秒
        self.number_frames = 0
        self.duration = 1 / self._fps * Gst.SECOND  # duration of a frame in nanoseconds
        # self.duration = 1 / self._fps * 1000

        self.launch_string = 'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME ' \
                             'caps=video/x-raw,format=BGR,width={},height={},framerate={}/1 ' \
                             '! videoconvert ! video/x-raw,format={} ' \
                             '! x264enc speed-preset=ultrafast tune=zerolatency ' \
                             '! rtph264pay config-interval=1 name=pay0 pt=96'.format(self._width, self._height,
                                                                                     self._fps, self._format)

        self.pipeline = Gst.parse_launch(self.launch_string)
        self.appsrc = self.pipeline.get_child_by_name('source')
        # todo xxx
        self.appsrc.get_property('caps').fixate()
        # self.appsrc.set_property('format', Gst.Format.TIME)
        self.bus = self.appsrc.get_bus()
        self.appsrc.connect('need-data', self.on_need_data)
        self.bus.connect('message::error', self.on_error)
        self.bus.connect('message::state-changed', self.on_status_changed)
        self.bus.connect('message::eos', self.on_eos)

        self._pass_count = 0

    def __del__(self):
        logger.debug('release capture')
        self.cap.release()



    def on_need_data(self, src, lenght):
        ret, frame = self.cap.read_raw()
        if ret:
            data = frame.tostring()
            buf = Gst.Buffer.new_allocate(None, len(data), None)
            buf.fill(0, data)
            buf.duration = self.duration
            timestamp = self.number_frames * self.duration
            buf.pts = buf.dts = int(timestamp)
            buf.offset = timestamp
            self.number_frames += 1
            retval = src.emit('push-buffer', buf)
            logger.debug('pushed buffer, frame {}, duration {} ns, durations {} s'.format(self.number_frames,
                                                                                          self.duration,
                                                                                          self.duration / Gst.SECOND))
            if retval != Gst.FlowReturn.OK:
                logger.debug(retval)

    def on_status_changed(self, bus, message):
        msg = message.parse_state_changed()
        logger.debug('status_changed message -> {}'.format(msg))

    def on_eos(self, bus, message):
        logger.debug('eos message -> {}'.format(message))

    def on_error(self, bus, message):
        logger.error('error message -> {}'.format(message.parse_error().debug))

    def do_create_element(self, url):
        return self.pipeline

    # def do_configure(self, rtsp_media):
    #     self.number_frames = 0
    #     appsrc = rtsp_media.get_element().get_child_by_name('source')
    #     appsrc.connect('need-data', self.on_need_data)


class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, stream_source, **properties):
        super(GstServer, self).__init__(**properties)
        self.factory = SensorFactory()
        self.factory.set_shared(True)
        self.get_mount_points().add_factory("/test", self.factory)
        self.attach(None)


GObject.threads_init()
Gst.init(None)

server = GstServer(0)

loop = GObject.MainLoop()
loop.run()
