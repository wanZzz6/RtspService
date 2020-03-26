#!/usr/bin/env python
# install gir1.2-gst-rtsp-server-1.0

import gi

import Feed
from logging_config import getLogger

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

GObject.threads_init()
Gst.init(None)
logger = getLogger('gi_camera_server')

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 450
DEFAULT_FPS = 20


class MediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, feed: Feed.Feed, **properties):
        super(MediaFactory, self).__init__(**properties)
        self.feed = feed
        self._height, self._width, self._fps = feed.get_h_w_fps()

        self._format = 'I420'
        self.number_frames = 0
        self.duration = 1 / self._fps * Gst.SECOND  # duration of a frame in nanoseconds
        # self.duration = 1 / self._fps * 1000

        self.launch_string = 'appsrc name={} is-live=true block=true format=GST_FORMAT_TIME ' \
                             'caps=video/x-raw,format=BGR,width={},height={},framerate={}/1 ' \
                             '! videoconvert ! video/x-raw,format={} ' \
                             '! x264enc speed-preset=ultrafast tune=zerolatency ' \
                             '! rtph264pay config-interval=1 name=pay0 pt=96'.format(self.feed.name, self._width,
                                                                                     self._height,
                                                                                     self._fps, self._format)

    def __del__(self):
        logger.debug('release capture')
        self.feed.close()

    def on_need_data(self, src, lenght):
        data = self.feed.feed().tostring()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.duration = self.duration
        timestamp = self.number_frames * self.duration
        buf.pts = buf.dts = int(timestamp)
        buf.offset = timestamp
        self.number_frames += 1
        retval = src.emit('push-buffer', buf)
        # logger.debug('pushed buffer, frame {}, duration {} ns, durations {} s'.format(self.number_frames,
        #                                                                               self.duration,
        #                                                                               self.duration / Gst.SECOND))
        logger.debug('pushed buffer, frame {}, durations {} s'.format(self.number_frames,
                                                                      self.duration / Gst.SECOND))
        if retval != Gst.FlowReturn.OK:
            logger.debug(retval)

    def on_status_changed(self, bus, message):
        change = message.parse_state_changed()

        change = message.parse_state_changed()
        logger.debug("%s State changed from %s -> %s\n" % (
            message.src.get_name(),
            change.oldstate.value_nick,
            change.newstate.value_nick
        ))

    def on_eos(self, bus, message):
        logger.debug('End of stream -> {}'.format(message))

    def on_error(self, bus, message):
        err, debug = message.parse_error()
        logger.error('error message -> {}: {}'.format(err, debug))

    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)

    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name(self.feed.name)
        appsrc.connect('need-data', self.on_need_data)

        bus = appsrc.get_bus()
        bus.connect('message::error', self.on_error)
        bus.connect('message::state-changed', self.on_status_changed)
        bus.connect('message::eos', self.on_eos)


class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, feed, access_path, port=8554, **properties):
        """
        :param feed:  Feed
        :param access_path: like: "/test"
        :param properties:
        """
        super(GstServer, self).__init__(**properties)
        self.set_service(str(port))
        self.connect("client-connected", self.on_client_connected)

        self.factory = MediaFactory(feed)
        self.factory.set_shared(True)
        mounts = self.get_mount_points()
        mounts.add_factory(access_path, self.factory)
        self.attach(None)

    def on_client_connected(self, server, client):
        logger.debug("client %s connected" % (client.get_connection().get_ip()))


if __name__ == '__main__':
    from analyse.algorithm import draw_rectangle

    url = 'rtsp://admin:admin777@10.86.77.12:554/h264/ch1/sub/av_stream'
    # url = 'rtmp://58.200.131.2:1935/livetv/hunantv'
    feed = Feed.OpenCvFeed(url, name='test', algor_handler=draw_rectangle)

    server = GstServer(feed, '/test', port=8555)
    loop = GObject.MainLoop()
    loop.run()
