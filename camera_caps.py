#!/usr/bin/env python3
#
#  Camera Capabilities
#
#  Copyright (C) 2021-22 JetsonHacks (info@jetsonhacks.com)
#
#  MIT License
#

import sys
from dataclasses import dataclass

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
                             QLabel, QLayout, QLineEdit, QListWidget,
                             QMainWindow, QPushButton, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)

from camera_caps_controller import Camera_Caps_Controller
from preview_window import PreviewWindow



@dataclass
class Camera_Caps_Config:
    window_width: int = 640
    window_height: int = 720
    top_frame_height: int = 310


window_configs = Camera_Caps_Config()


class Camera_Caps_Window(QMainWindow):

    def setup(self, controller):

        self.ctrl_dict = {}  # Holds control groups accessed by v4l2 control name
        top_frame = self.setup_top_frame(controller)
        self.setCentralWidget(top_frame)
        self.setGeometry(100, 100, window_configs.window_width,
                         window_configs.window_height)
        self.setWindowTitle('Camera Capabilities')

    def setup_top_frame(self, controller):
        main_frame = QFrame()
        main_vbox = QVBoxLayout()
        main_frame.setLayout(main_vbox)

        top_frame = QFrame()
        top_vbox = QVBoxLayout()
        top_frame.setLayout(top_vbox)
        top_frame.setMaximumHeight(window_configs.top_frame_height)

        camera_box = QHBoxLayout()
        camera_label = QLabel("Camera")
        camera_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        camera_box.addWidget(camera_label)

        self.camera_combo_box = QComboBox(self)
        self.camera_combo_box.setSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.camera_combo_box.currentIndexChanged.connect(
            controller.on_camera_box_changed)
        camera_box.addWidget(self.camera_combo_box)
        camera_box.addStretch()
        top_vbox.addLayout(camera_box)

        self.driver_label = QLabel("Driver")
        self.bus_label = QLabel("Bus")
        self.capabilities_label = QLabel("Capabilities")
        self.device_capabilities_label = QLabel("Device Caps")
        for label in [self.bus_label, self.driver_label,  self.capabilities_label, self.device_capabilities_label]:
            top_vbox.addWidget(label)
        main_vbox.addWidget(top_frame)

        middle_frame = self.setup_middle_frame(controller)
        top_vbox.addWidget(middle_frame)

        preview_frame = self.setup_preview_frame(controller)
        top_vbox.addWidget(preview_frame)

        self.bottom_frame = self.setup_control_menu_frame(controller)
        main_vbox.addWidget(self.bottom_frame)

        return main_frame

    def setup_middle_frame(self, controller):
        middle_frame = QFrame()
        middle_hbox = QHBoxLayout()
        middle_frame.setLayout(middle_hbox)

        # List of pixel formats
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Pixel Format"))
        self.pixel_format_list = QListWidget()
        self.pixel_format_list.setMinimumWidth(280)
        self.pixel_format_list.itemClicked.connect(
            controller.on_pixel_format_list_clicked)
        vbox.addWidget(self.pixel_format_list)
        # middle_hbox.addWidget(self.pixel_format_list)
        middle_hbox.addLayout(vbox)

        # Image Size list
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Image Size"))
        self.image_size_list = QListWidget()
        self.image_size_list.setMinimumWidth(280)
        self.image_size_list.itemClicked.connect(
            controller.on_image_size_list_clicked)
        vbox.addWidget(self.image_size_list)
        middle_hbox.addLayout(vbox)

        # FPS list
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Frame Duration"))
        self.fps_list = QListWidget()
        self.fps_list.setMinimumWidth(280)
        self.fps_list.itemClicked.connect(controller.on_fps_list_clicked)
        vbox.addWidget(self.fps_list)
        middle_hbox.addLayout(vbox)

        return middle_frame

    def setup_preview_frame(self, controller):
        self.preview = QWidget()
        preview_hbox = QHBoxLayout()
        self.preview.setLayout(preview_hbox)
        self.line_edit = QLineEdit()
        self.line_edit.setText(
            "v4l2src device=/dev/video4 ! video/x-raw, width=640, height=480, framerate=30/1 ! xvimagesink")
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

        return self.preview

    def setup_control_menu_frame(self, controller):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        # scroll_vbox = QVBoxLayout()
        # self.scroll.setLayout(scroll_vbox)

        self.control_menu_frame = QFrame()
        control_menu_vbox = QVBoxLayout()
        self.control_menu_frame.setLayout(control_menu_vbox)

        self.scroll.setWidget(self.control_menu_frame)
        # return self.control_menu_frame
        return self.scroll

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
        # preview_window.show()
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
