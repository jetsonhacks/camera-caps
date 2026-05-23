#!/usr/bin/env python3
#
#  Camera Capabilities
#
#  Copyright (C) 2021-22 JetsonHacks (info@jetsonhacks.com)
#
#  MIT License
#

import sys
import os
from dataclasses import dataclass

from camera_caps.gst.environment import import_gst
from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
                             QLabel, QLayout, QLineEdit, QListWidget, QCheckBox,
                             QMainWindow, QPushButton, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)

from camera_caps_controller import Camera_Caps_Controller
from preview_window import PreviewWindow


Gst, _GstVideo = import_gst()


@dataclass
class Camera_Caps_Config:
    window_width: int = 640
    window_height: int = 720

window_configs = Camera_Caps_Config()

class Camera_Caps_Window(QMainWindow):

    def setup(self, controller):

        self.ctrl_dict = {}  # Holds control groups accessed by v4l2 control name
        top_frame = self.setup_top_frame(controller)
        self.setCentralWidget(top_frame)
        self.setGeometry(100, 100, window_configs.window_width,
                         window_configs.window_height)
        self.setWindowTitle('Camera Capabilities')
        if os.environ.get("CAMERA_CAPS_LAYOUT_DEBUG"):
            QTimer.singleShot(0, self.debug_layout_state)

    def setup_top_frame(self, controller):
        main_frame = QFrame()
        main_vbox = QVBoxLayout()
        main_frame.setLayout(main_vbox)
        layout_spacing = max(8, self.fontMetrics().height() // 2)
        main_vbox.setContentsMargins(layout_spacing, layout_spacing,
                                     layout_spacing, layout_spacing)
        main_vbox.setSpacing(layout_spacing)

        top_frame = QFrame()
        top_vbox = QVBoxLayout()
        top_frame.setLayout(top_vbox)
        top_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        top_vbox.setContentsMargins(0, 0, 0, 0)
        top_vbox.setSpacing(max(4, layout_spacing // 2))

        camera_box = QHBoxLayout()
        camera_box.setContentsMargins(0, 0, 0, 0)
        camera_label = QLabel("Camera")
        camera_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        camera_box.addWidget(camera_label)

        self.camera_combo_box = QComboBox(self)
        self.camera_combo_box.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.camera_combo_box.currentIndexChanged.connect(
            controller.on_camera_box_changed)
        camera_box.addWidget(self.camera_combo_box)
        top_vbox.addLayout(camera_box)

        self.driver_label = QLabel("Driver")
        self.bus_label = QLabel("Bus")
        self.capabilities_label = QLabel("Capabilities")
        self.device_capabilities_label = QLabel("Device Caps")
        for label in [self.bus_label, self.driver_label,  self.capabilities_label, self.device_capabilities_label]:
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            top_vbox.addWidget(label)
        main_vbox.addWidget(top_frame, 0)

        middle_frame = self.setup_middle_frame(controller)
        main_vbox.addWidget(middle_frame, 1)

        preview_frame = self.setup_preview_frame(controller)
        main_vbox.addWidget(preview_frame, 0)

        self.bottom_frame = self.setup_control_menu_frame(controller)
        main_vbox.addWidget(self.bottom_frame, 2)

        return main_frame

    def setup_middle_frame(self, controller):
        layout_spacing = max(8, self.fontMetrics().height() // 2)
        middle_frame = QFrame()
        middle_hbox = QHBoxLayout()
        middle_frame.setLayout(middle_hbox)
        middle_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        middle_hbox.setContentsMargins(0, 0, 0, 0)
        middle_hbox.setSpacing(layout_spacing)

        # List of pixel formats
        vbox = QVBoxLayout()
        vbox.setSpacing(max(4, layout_spacing // 2))
        pixel_format_label = QLabel("Pixel Format")
        pixel_format_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        vbox.addWidget(pixel_format_label)
        self.pixel_format_list = QListWidget()
        self.pixel_format_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pixel_format_list.itemClicked.connect(
            controller.on_pixel_format_list_clicked)
        vbox.addWidget(self.pixel_format_list)
        # middle_hbox.addWidget(self.pixel_format_list)
        middle_hbox.addLayout(vbox, 1)

        # Image Size list
        vbox = QVBoxLayout()
        vbox.setSpacing(max(4, layout_spacing // 2))
        image_size_label = QLabel("Image Size")
        image_size_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        vbox.addWidget(image_size_label)
        self.image_size_list = QListWidget()
        self.image_size_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_size_list.itemClicked.connect(
            controller.on_image_size_list_clicked)
        vbox.addWidget(self.image_size_list)
        middle_hbox.addLayout(vbox, 1)

        # FPS list
        vbox = QVBoxLayout()
        vbox.setSpacing(max(4, layout_spacing // 2))
        fps_label = QLabel("Frame Duration")
        fps_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        vbox.addWidget(fps_label)
        self.fps_list = QListWidget()
        self.fps_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.fps_list.itemClicked.connect(controller.on_fps_list_clicked)
        vbox.addWidget(self.fps_list)
        middle_hbox.addLayout(vbox, 1)

        return middle_frame

    def setup_preview_frame(self, controller):
        self.preview = QWidget()
        preview_hbox = QHBoxLayout()
        self.preview.setLayout(preview_hbox)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        preview_hbox.setContentsMargins(0, 0, 0, 0)
        preview_hbox.setSpacing(max(4, self.fontMetrics().height() // 2))
        self.line_edit = QLineEdit()
        # self.line_edit.setText(
        #    "v4l2src device=/dev/video4 ! video/x-raw, width=640, height=480, framerate=30/1 ! xvimagesink")
        self.line_edit.setText("")
        preview_hbox.addWidget(self.line_edit)

        self.copy_button = QPushButton('')
        self.copy_button.line_edit = self.line_edit
        self.copy_button.setIcon(QIcon('baseline_content_copy_black_24dp.png'))
        self.copy_button.setIconSize(QSize(24, 24))   
        self.copy_button.clicked.connect(controller.copy_button_clicked)
        preview_hbox.addWidget(self.copy_button)

        self.preview_button = QPushButton('')
        self.preview_button.line_edit = self.line_edit
        self.preview_button.setIcon(QIcon('baseline_preview_black_24dp.png'))
        self.preview_button.setIconSize(QSize(24, 24))   
        self.preview_button.clicked.connect(controller.preview_button_clicked)
        preview_hbox.addWidget(self.preview_button)

        self.sync_flag_checkbox = QCheckBox('Synchronize Video')
        self.sync_flag_checkbox.clicked.connect(controller.on_sync_flag_checkbox_clicked)
        preview_hbox.addWidget(self.sync_flag_checkbox)

        return self.preview

    def setup_control_menu_frame(self, controller):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # scroll_vbox = QVBoxLayout()
        # self.scroll.setLayout(scroll_vbox)

        self.control_menu_frame = QFrame()
        control_menu_vbox = QVBoxLayout()
        self.control_menu_frame.setLayout(control_menu_vbox)

        self.scroll.setWidget(self.control_menu_frame)
        # return self.control_menu_frame
        return self.scroll

    def debug_layout_state(self):
        preview_size = self.preview.size()
        print(
            "Layout debug: "
            f"pixel formats={self.pixel_format_list.count()}, "
            f"image sizes={self.image_size_list.count()}, "
            f"fps={self.fps_list.count()}, "
            f"preview visible={self.preview.isVisible()}, "
            f"preview size={preview_size.width()}x{preview_size.height()}"
        )

    def clear_layout(self, layout: QLayout):
        self.ctrl_dict = {}         # Clear out previous ctrl groups
        child = layout.takeAt(0)
        while child is not None:
            if child.layout() is not None:
                self.clear_layout(child.layout())
            elif child.widget() is not None:
                layout.removeWidget(child.widget())
                child.widget().setParent(None)
            child = layout.takeAt(0)

    def create_preview_window(self):
        preview_window = PreviewWindow()
        preview_window.setup()
        return preview_window

    def closeEvent(self, event):
        # Closing this window terminates the application
        for window in self.preview_windows:
            window.app_closing = True
            window.close()

def main():
    Gst.init(None)
    app = QApplication(sys.argv)
    window = Camera_Caps_Window()
    window.preview_windows = window.create_preview_window()
    controller = Camera_Caps_Controller(window)
    controller.setup()

    """ 
    def quitting_app():
        controller.app_quitting()
    """

    app.aboutToQuit.connect(controller.app_quitting)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
