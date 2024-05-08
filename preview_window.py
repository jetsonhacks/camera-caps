#
#  Camera Preview Window
#
#  Copyright (C) 2021-22 JetsonHacks (info@jetsonhacks.com)
#
#  MIT License
#
from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget
from PyQt5.QtGui import QMouseEvent, QPaintEvent, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QEvent
from PyQt5.QtCore import qInstallMessageHandler, QtDebugMsg, QtWarningMsg, QtCriticalMsg, QtFatalMsg

import time

import gi
from gi.repository import Gst, GstVideo

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

import camera_caps_dataclasses

def messageFilter(mode, context, message):
    if "Overlay is ready" in message:
        print("Got overlay message")
        return  # Suppress specific message
    else:
        # Default handler behavior (you can replace this with your own handling logic)
        print(message)

qInstallMessageHandler(messageFilter)

# GstVideo is required for running video for GstXvImageSink in QWidget


class PreviewWindow(QMainWindow):

    # Define signals that broadcast geometry changes
    windowMoved = pyqtSignal(QRect)
    windowResized = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super(PreviewWindow, self).__init__(parent)


    def setup(self):
        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.StrongFocus)
        video_frame = self.setup_video_frame()
        self.setCentralWidget(video_frame)
        self.setStyleSheet("background-color:black;")
        # The device uri of the camera
        self.device_uri = None
        self.base_title = ""
        self.video_widget.winId = self.video_widget.winId()
        self.video_widget.pipeline = None
        self.app_closing = False
        # camera_settings is the current caps filter for the camera
        self.camera_settings = None
        self.setGeometry(100, 100, 640, 480)
        self.setWindowTitle('Video Window')
        self.overlay_window = TransparentOverlay()
        # self.overlay_window.parent = self
        self.overlay_window.video_window = self
        self.overlay_window.setGeometry(100, 100, 640, 480)
        self.overlay_window.hide()
        # Connect the move and resize signals to the overlay adjustment slot
        self.windowMoved.connect(self.overlay_window.updatePosition)
        self.windowResized.connect(self.overlay_window.updatePosition)


    def show(self):
        super().show()
        self.overlay_window.show()
        
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
            self.overlay_window.close()
            # If there's a pipeline, stop it and dispose
            if self.video_widget.pipeline is not None:
                self.video_widget.close_pipeline()
            event.accept()
        else:
            # Emitting event.accept() closes window; we want to hide it instead
            event.ignore()
            self.hide()
            self.overlay_window.hide()
            # If there's a pipeline, stop it and dispose
            if self.video_widget.pipeline is not None:
                self.video_widget.close_pipeline()

    # Map the client area's rectangle to global coordinates
    def global_client_rect(self):
        global_top_left = self.mapToGlobal(self.rect().topLeft())
        global_bottom_right = self.mapToGlobal(self.rect().bottomRight())
        # Create a QRect from these global coordinates
        global_rect = QRect(global_top_left, global_bottom_right)
        return global_rect
    
        
    def get_global_rectangle(self, widget):
        # Calculate the global position of the top-left corner
        global_top_left = widget.mapToGlobal(widget.pos())
        # Create a QRect representing the global rectangle
        global_rect = QRect(global_top_left, widget.size())
        return global_rect
    
    def getClientAreaOffset(self):
        # Global position of the window's top-left corner including decorations
        frame_origin_global = self.frameGeometry().topLeft()

        # Global position of the client area's top-left corner
        client_origin_global = self.mapToGlobal(self.rect().topLeft())
        # Calculate the offset by subtracting these two global positions
        offset = client_origin_global - frame_origin_global
        return offset

    
    def moveEvent(self, event):
        super().moveEvent(event)
        global_rect = self.global_client_rect()
        global_rect = self.get_global_rectangle(self.video_widget)
        # Emit the signal with the QRect
        self.windowMoved.emit(global_rect)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        global_rect = self.global_client_rect()
        global_rect = self.get_global_rectangle(self.video_widget)
        # Emit the signal with the QRect
        self.windowResized.emit(global_rect)

    # Show the overlay window when this window is activated   
    def changeEvent(self, event):

        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():              
                if not self.isMaximized():
                    # Double click on title bar?
                    self.overlay_window.show()
                    self.overlay_window.activateWindow()
        elif event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMaximized:
                # Actions to perform when the window is maximized
                global_rect = self.global_client_rect()
                global_rect = self.get_global_rectangle(self.video_widget)
                # Emit the signal with the QRect
                self.windowResized.emit(global_rect)
                if not self.isHidden():
                    self.overlay_window.show()
                    self.overlay_window.activateWindow()

            elif event.oldState() & Qt.WindowMaximized:
                # Actions to perform when the window is restored from maximized
                global_rect = self.global_client_rect()
                global_rect = self.get_global_rectangle(self.video_widget)
                # Emit the signal with the QRect
                self.windowResized.emit(global_rect)
                if not self.isHidden():
                    self.overlay_window.show()
                    self.overlay_window.activateWindow()
        super(PreviewWindow, self).changeEvent(event)


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.onEscPressed()

    def onEscPressed(self):
        print("Escape key was pressed!")
        # Reset the videocrop
        pipeline = self.video_widget.pipeline
        cropper = pipeline.get_by_name("cropper")
        cropper.set_property('top', 0)
        cropper.set_property('left', 0)
        cropper.set_property('bottom', 0)
        cropper.set_property('right', 0)

         # self.hide()
        
    def translate_coordinates_aspect_ratio(self, window_width, window_height, video_width, video_height, rect_x, rect_y, rect_width, rect_height):
        """
        Translate coordinates from display window to original video frame, preserving aspect ratio and ensuring the rectangle is within video bounds.

        Parameters:
        - window_width (int): Width of the window where the video is displayed.
        - window_height (int): Height of the window where the video is displayed.
        - video_width (int): Original width of the video.
        - video_height (int): Original height of the video.
        - rect_x (int): X-coordinate of the upper-left corner of the rectangle in window coordinates.
        - rect_y (int): Y-coordinate of the upper-left corner of the rectangle in window coordinates.
        - rect_width (int): Width of the rectangle in window coordinates.
        - rect_height (int): Height of the rectangle in window coordinates.

        Returns:
        - (tuple): A tuple containing the translated and clipped rectangle coordinates (x, y, width, height) in the video frame reference.
        """
        # Calculate aspect ratios and determine scaling and offset
        window_ratio = window_width / window_height
        video_ratio = video_width / video_height

        if window_ratio > video_ratio:
            # Pillarboxing (black bars on the sides)
            scale = window_height / video_height
            scaled_video_width = video_width * scale
            offset_x = (window_width - scaled_video_width) / 2
            offset_y = 0
        else:
            # Letterboxing (black bars on top and bottom)
            scale = window_width / video_width
            scaled_video_height = video_height * scale
            offset_x = 0
            offset_y = (window_height - scaled_video_height) / 2

        # Translate and scale window coordinates to video frame coordinates
        video_x = (rect_x - offset_x) / scale
        video_y = (rect_y - offset_y) / scale
        video_w = rect_width / scale
        video_h = rect_height / scale

        # Normalize and clip the rectangle to ensure it doesn't go out of the video bounds
        video_x = max(0, min(video_x, video_width))
        video_y = max(0, min(video_y, video_height))
        video_w = max(0, min(video_w, video_width - video_x))
        video_h = max(0, min(video_h, video_height - video_y))

        return (int(video_x), int(video_y), int(video_w), int(video_h))

    
    def print_pipeline_elements(self,pipeline):
        """
        Print the names and types of    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Map the client area's rectangle to global coordinates and emit
        global_rect = self.mapToGlobal(self.rect().topLeft()), self.mapToGlobal(self.rect().bottomRight())
        self.windowResized.emit(QRect(global_rect[0], global_rect[1].x() - global_rect[0].x(), global_rect[1].y() - global_rect[0].y())) all elements in a GStreamer pipeline.

        Parameters:
        - pipeline (Gst.Pipeline): The GStreamer pipeline object.
        """
        # Iterate through all elements in the pipeline
        iterator = pipeline.iterate_elements()
        while True:
            result, element = iterator.next()
            if result != Gst.IteratorResult.OK:
                # Break out of the loop if no more elements
                break
            if element:
                print(f"Element Name: {element.get_name()}, Element Type: {element.__gtype__.name}")


    def query_caps(self, pipeline, element_name):
        """
        Query the negotiated capabilities of a specified element within a pipeline.
        
        Parameters:
        - pipeline (Gst.Pipeline): The GStreamer pipeline object.
        - element_name (str): The name of the element to query.

        Returns:
        - (int, int): Width and height of the video or (None, None) if not found.
        """
        # self.print_pipeline_elements(pipeline)
        element = pipeline.get_by_name(element_name)
        if element:
            pad = element.get_static_pad('src' if element_name != 'xvimagesink0' else 'sink')
            if pad:
                caps = pad.get_current_caps()
                if caps:
                    structure = caps.get_structure(0)
                    if structure:
                        width = structure.get_int('width').value
                        height = structure.get_int('height').value
                        return width, height
        return None, None
    
    # Function to dynamically add a videocrop element
    def add_videocrop(pipeline):
        pipeline.set_state(Gst.State.PAUSED)  # Pause the pipeline

        # Create a videocrop element
        videocrop = Gst.ElementFactory.make("videocrop", "cropper")
        pipeline.add(videocrop)

        # Get the videoconvert and sink elements
        videoconvert = pipeline.get_by_name("videoconvert0")
        videosink = pipeline.get_by_name("xvimagesink0")

        # Unlink videoconvert from videosink
        videoconvert.unlink(videosink)

        # Link videoconvert -> videocrop -> videosink
        videoconvert.link(videocrop)
        videocrop.link(videosink)

        # Set videocrop properties, if necessary
        videocrop.set_property('top', 50)
        videocrop.set_property('left', 50)
        videocrop.set_property('right', 50)
        videocrop.set_property('bottom', 50)

        pipeline.set_state(Gst.State.PLAYING)  # Set the pipeline back to 
        # playing

    def calculate_scale_to_fit(self,cropped_width, cropped_height, window_width, window_height):
        """
        Calculate the scale factor to fit a cropped video frame into a window while preserving the aspect ratio.
        
        Parameters:
        cropped_width (int): Width of the cropped video frame.
        cropped_height (int): Height of the cropped video frame.
        window_width (int): Width of the display window.
        window_height (int): Height of the display window.
        
        Returns:
        float: Scale factor needed to fit the cropped frame into the window.
        """
        # Calculate scale factors for both dimensions
        scale_factor_width = window_width / cropped_width
        scale_factor_height = window_height / cropped_height

        # Use the minimum scale factor to preserve aspect ratio
        scale_factor = min(scale_factor_width, scale_factor_height)

        return scale_factor
    
    def set_roi ( self, screen_rect: QRect) :
        pipeline = self.video_widget.pipeline
        video_width = int(self.camera_settings.image_width)
        video_height = int(self.camera_settings.image_height)

        # def translate_coordinates_aspect_ratio(self, window_width, window_height, video_width, video_height, rect_x, rect_y, rect_width, rect_height):
        translated_coordinates = self.translate_coordinates_aspect_ratio(self.width(), self.height(), video_width, video_height,  
                                                                         screen_rect.x(), screen_rect.y(), screen_rect.width(), screen_rect.height())
        # print(f"Translated coordinates: {translated_coordinates}")
        # Retrieve the videocrop element
        cropper = pipeline.get_by_name("cropper")
        # Calculate the scale factor
        # scale_factor = self.calculate_scale_to_fit(translated_coordinates[2], translated_coordinates[3], self.width(), self.height())
        # print(f"Scale factor: {scale_factor}")
        # Setup the amount to crop from each side
        bottom_offset = video_height - (translated_coordinates[1] + translated_coordinates[3])
        right_offset = video_width - (translated_coordinates[0] + translated_coordinates[2])
        print(f"Crop rect: {translated_coordinates[1]}@{translated_coordinates[0]} x {bottom_offset}@{right_offset}")
        cropper.set_property('top', translated_coordinates[1])
        cropper.set_property('left', translated_coordinates[0])
        cropper.set_property('bottom', bottom_offset)
        cropper.set_property('right', right_offset)

class VideoWidget(QMainWindow):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.pipeline = None
        self.start_point = None
        self.end_point = None

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
        print(launch_cmd)
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

    def pause_pipeline(self):
        self.pipeline.set_state(Gst.State.PAUSED)

    
class TransparentOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_window = None
        self.start_point = None
        self.end_point = None
        self.roi_rectangle = None  # This will store the current ROI as a QRect
        self.setFocusPolicy(Qt.StrongFocus)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Overlay')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(300, 300, 400, 300)  # Set geometry to match or cover the target window

    def updatePosition(self, new_geometry):        
        # Check if new_geometry is a QRect
        if isinstance(new_geometry, QRect):
            self.setGeometry(new_geometry)
            self.move(new_geometry.topLeft())
        # Check if new_geometry is a tuple or list and has four integer elements
        elif isinstance(new_geometry, (tuple, list)) and len(new_geometry) == 4 and all(isinstance(n, int) for n in new_geometry):
            self.setGeometry(*new_geometry)
        else:
            print("Invalid geometry format")


    def mousePressEvent(self, event):
        if self.roi_rectangle is None:
            self.start_point = event.pos()
            self.end_point = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.roi_rectangle is None:
            if event.buttons() == Qt.LeftButton:
                self.end_point = event.pos()
                self.update()

    def mouseReleaseEvent(self, event):
        if self.roi_rectangle is None:
            self.end_point = event.pos()
            self.update()
            # Set the ROI rectangle based on the start and end points
            if self.start_point and self.end_point:
                self.roi_rectangle = QRect(self.start_point, self.end_point)
                self.roi_rectangle = self.roi_rectangle.normalized()  # Normalize to ensure correct geometry
                print(f"ROI set to: {self.roi_rectangle}")  # Optionally print or log the ROI for debugging
                self.video_window.set_roi(self.roi_rectangle)
            self.start_point = None
            self.end_point = None

    def paintEvent(self, event):
        self.setAttribute(Qt.WA_TranslucentBackground)
        super().paintEvent(event)
        if self.start_point and self.end_point:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            painter.drawRect(QRect(self.start_point, self.end_point))

        return
        # Show the bounds of the TransparentOverlay window
        painter_red = QPainter(self)
        painter_red.setPen(QPen(Qt.darkCyan, 1, Qt.SolidLine))
        painter_red.drawRect(2, 2, self.width() - 4, self.height() - 4)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.onEscPressed()

    def onEscPressed(self):
        self.video_window.onEscPressed() 
        self.roi_rectangle = None

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.start_point = None
        self.end_point = None

    # When we lose focus, hide us so we don't get mouse events
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.hide()
        self.start_point = None
        self.end_point = None

    def resizeEvent(self, event):
        # Print the new size
        if self.windowState() == Qt.WindowMaximized:
            return
        # Call the base class method to ensure proper handling
        super().resizeEvent(event)


