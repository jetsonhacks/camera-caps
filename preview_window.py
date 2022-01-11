#
#  Camera Preview Window
#
#  Copyright (C) 2021-22 JetsonHacks (info@jetsonhacks.com)
#
#  MIT License
#
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QWidget)
import time

import gi
from gi.repository import Gst, GstVideo

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')


# GstVideo is required for running video for GstXvImageSink in QWidget


class PreviewWindow(QMainWindow):

    def setup(self):
        # self.setWindowFlags(Qt.FramelessWindowHint)
        video_frame = self.setup_video_frame()
        self.setCentralWidget(video_frame)
        self.setStyleSheet("background-color:black;")
        # The device uri of the camera
        self.device_uri = None
        self.base_title = ""
        self.video_widget.winId = self.video_widget.winId()
        self.video_widget.pipeline = None
        self.app_closing = False
        self.setGeometry(100, 100, 640, 480)
        self.setWindowTitle('Video Window')

    def setup_video_frame(self):
        video_frame = QWidget()
        video_vbox = QVBoxLayout()
        video_frame.setLayout(video_vbox)
        self.video_widget = VideoWidget()
        video_vbox.addWidget(self.video_widget)
        video_vbox.setContentsMargins(0, 0, 0, 0)
        return video_frame

    def closeEvent(self, event):
        if self.app_closing is True:
            # The app is closing down; Closed caps dialog window
            # TODO - Should shutdown GStreamer pipelines here
            event.accept()
        else:
            # Emitting event.accept() closes window; we want to hide it instead
            event.ignore()
            self.hide()
            # If there's a pipeline, stop it and dispose
            if self.video_widget.pipeline is not None:
                self.video_widget.close_pipeline()

    """ 
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.oldPosition = event.globalPos()
        # return super().mousePressEvent(a0)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        delta = QPoint(event.globalPos() - self.oldPosition)
        self.move(self.x()+delta.x(),self.y() + delta.y())
        self.oldPosition = event.globalPos()
        # return super().mouseMoveEvent(a0)
    """


class VideoWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.pipeline = None

    def has_video(self):
        return self.pipeline is not None

    def close_pipeline(self):
        if self.pipeline is not None:
            self.stop_pipeline()
            # Wait for the pipeline to stop everything
            # before deallocating
            time.sleep(1)
            self.pipeline = None

    def setup_pipeline(self, launch_cmd):

        # Working Test Patterns
        # launch_str = "videotestsrc ! video/x-raw,width=640,height=480 ! videoconvert ! xvimagesink"
        # launch_str = "videotestsrc ! video/x-raw,width=640,height=480 ! videoconvert ! xvimagesink render-rectangle=\"<10,10,320,240>\""
        # Working CSI Camera
        # launch_str = "nvarguscamerasrc ! video/x-raw(memory:NVMM),width=1280, height=720, framerate=60/1, format=NV12 ! nvvidconv flip-method=0 ! video/x-raw,width=640, height=360 ! nvvidconv ! xvimagesink "
        # USB Camera
        # launch_str = "v4l2src device=/dev/video1 ! video/x-raw,framerate=30/1,width=640,height=480 ! xvimagesink"

        # ToDo - Try Except block, check to see if string parsed
        self.pipeline = Gst.parse_launch(launch_cmd)
        self.cmd_line = launch_cmd

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

    def on_message(self, bus, message):
        message_type = message.type
        if message_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Bus error message: {err} {debug}")

    def on_sync_message(self, bus, message):
        structure = message.get_structure()
        if structure is None:
            return
        message_name = structure.get_name()

        if message_name == "prepare-window-handle":
            assert self.winId
            # Message.src should be a sink, e.g. GstXvImageSink
            message.src.set_window_handle(self.winId)

    def start_pipeline(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop_pipeline(self):
        self.pipeline.set_state(Gst.State.NULL)
