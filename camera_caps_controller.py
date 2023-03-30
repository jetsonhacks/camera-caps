#
#  Camera Capabilities
#
#  Copyright (C) 2021-2022 JetsonHacks (info@jetsonhacks.com)
#
#  MIT License
#
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout,
                             QLabel, QListWidgetItem, QPushButton, QSizePolicy,
                             QSlider, QSpinBox, QVBoxLayout)
from dataclasses import dataclass

from camera_caps_model import (Camera_Format, Camera_Inspector,
                               Control_Menu_Entry)
from preview_window import PreviewWindow


class Command_Map:
    source: dict = {'uvcvideo': 'v4l2src device={device_uri}',
                    'tegra-video': 'nvarguscamerasrc sensor-id={}'}
    filters: dict = {'YUYV': 'video/x-raw, width={}, height={}, framerate={}/1 ! xvimagesink',
                     'H264': 'video/x-h264, width={}, height={}, framerate={}/1, format=H264 ! nvv4l2decoder ! nvvidconv ! xvimagesink sync=false',
                     'MJPG': 'image/jpeg, width={}, height={}, framerate={}/1, format=MJPG ! nvv4l2decoder mjpeg=1 ! nvvidconv ! xvimagesink',
                     'UYVY': 'video/x-raw, width={}, height={}, framerate={}/1, format=UYVY ! xvimagesink'}


class Camera_Caps_Controller:

    def __init__(self, view):
        self.view = view
        self.device_uri = None
        # list of camera device id and PIDs of camera running in preview window
        self.camera_preview_list = []
        self.check_previews_timer = None
        self.camera_inspector = Camera_Inspector()
        self.camera_list = self.camera_inspector.list_cameras()
        self.camera_location = None
        self.camera_formats = None
        self.size_list = None
        self.gst_source = ""
        self.gst_filters = ""
        self.image_width = ""   # Currently selected image width
        self.image_height = ""  # Currently selected image height
        self.frame_rate = "30"  # Currently select frame rate

    def setup(self):
        self.view.setup(self)
        preview_window_list = []
        if len(self.camera_list) > 0:
            self.view.camera_combo_box.setEnabled(True)
            for camera in self.camera_list:
                for uri in camera.uri_list:
                    entry_name = f"{camera.camera_name} on {uri}"
                    self.view.camera_combo_box.addItem(entry_name, uri)
                    item_index = self.view.camera_combo_box.count()
                    # Does the camera have associated formats?
                    formats = self.camera_inspector.camera_formats(uri)
                    if len(formats) == 0:
                        self.view.camera_combo_box.model().item(item_index-1).setEnabled(False)
                    # Create a preview window for the camera
                    preview_window: PreviewWindow = self.view.create_preview_window()
                    preview_window.base_title = entry_name
                    preview_window.setWindowTitle(entry_name)
                    preview_window.device_uri = uri
                    preview_window_list.append(preview_window)
        else:
            # No cameras to show
            self.view.camera_combo_box.setEnabled(False)
        self.view.preview_windows = preview_window_list
        self.view.show()

    def set_ctl_value(self, setting, value):
        try:
            success_flag = subprocess.check_output(
                ["v4l2-ctl", '-d', self.device_uri, '-c', f"{setting}={value}"], encoding='utf-8')
        except Exception as exc:
            print(exc)

    def add_ctrl_slider(self, ctrl_menu: Control_Menu_Entry):
        slider_menu_vbox = QVBoxLayout()
        slider_menu_vbox.ctl_name = ctrl_menu.title
        inactive_flag = False
        for item in ctrl_menu.key_value_list:
            if item[0] == 'flags' and item[1] == 'inactive':
                inactive_flag = True
                break

        label_text = str.replace(ctrl_menu.title, '_', ' ').title()
        label = QLabel(label_text)
        if inactive_flag == True:
            label.setEnabled(False)
        slider_menu_vbox.addWidget(label)

        slider_hbox = QHBoxLayout()
        slider_hbox.addSpacing(10)
        slider = QSlider(Qt.Horizontal)
        slider.ctrl_menu = ctrl_menu
        min_value = [item[1]
                     for item in ctrl_menu.key_value_list if item[0] == 'min'][0]
        slider.setMinimum(int(min_value))
        max_value = [item[1]
                     for item in ctrl_menu.key_value_list if item[0] == 'max'][0]
        slider.setMaximum(int(max_value))
        current_value = [item[1]
                         for item in ctrl_menu.key_value_list if item[0] == 'value'][0]
        slider.setValue(int(current_value))
        step_size = [item[1]
                     for item in ctrl_menu.key_value_list if item[0] == 'step'][0]
        slider.setSingleStep(int(step_size))

        default_value = [item[1]
                         for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
        slider.default_value = int(current_value)
        if default_value is not None:
            slider.default_value = int(default_value)

        slider_hbox.addWidget(slider)

        spin_box = QSpinBox()
        spin_box.setMaximum(slider.maximum())
        spin_box.setMinimum(slider.minimum())
        spin_box.setValue(int(current_value))
        spin_box.setSingleStep(int(step_size))
        spin_box.setAlignment(Qt.AlignRight)
        slider_hbox.addWidget(spin_box)
        spin_box.slider = slider
        slider.spin_box = spin_box

        slider.valueChanged.connect(self.onSliderValueChanged)
        spin_box.valueChanged.connect(self.onSpinBoxValueChanged)

        reset_button = QPushButton('Default')
        reset_button.ctrl_menu = ctrl_menu
        reset_button.clicked.connect(self.slider_reset_button_clicked)
        reset_button.slider = slider
        slider.reset_button = reset_button

        slider_hbox.addWidget(reset_button)

        if inactive_flag == True:
            slider.setEnabled(False)
            spin_box.setEnabled(False)
            reset_button.setEnabled(False)

        self.view.ctrl_dict[ctrl_menu.title] = [
            label, slider, spin_box, reset_button]

        slider_menu_vbox.addLayout(slider_hbox)
        layout = self.view.control_menu_frame.layout()
        layout.addLayout(slider_menu_vbox)

    def add_ctrl_bool(self, ctrl_menu: Control_Menu_Entry):
        label_text = str.replace(ctrl_menu.title, '_', ' ').title()
        check_box = QCheckBox(label_text)
        check_box.ctrl_menu = ctrl_menu
        layout = self.view.control_menu_frame.layout()
        value = [item[1]
                 for item in ctrl_menu.key_value_list if item[0] == 'value'][0]
        if value == '1':
            check_box.setChecked(True)
        else:
            check_box.setChecked(False)
        check_box.toggled.connect(self.check_box_onClicked)

        reset_button = QPushButton('Default')
        reset_button.ctrl_menu = ctrl_menu
        reset_button.check_box = check_box
        reset_button.clicked.connect(self.bool_reset_button_clicked)

        self.view.ctrl_dict[ctrl_menu.title] = [check_box, reset_button]

        bool_hbox = QHBoxLayout()
        bool_hbox.addSpacing(10)
        bool_hbox.addWidget(check_box)
        bool_hbox.addStretch()
        bool_hbox.addWidget(reset_button)

        layout.addLayout(bool_hbox)

    def add_ctrl_menu(self, ctrl_menu: Control_Menu_Entry):
        combo_box_menu_hbox = QHBoxLayout()
        label_text = str.replace(ctrl_menu.title, '_', ' ').title()
        label = QLabel(label_text)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        combo_box_menu_hbox.addWidget(label)
        combo_box_menu_hbox.setSpacing(10)
        combo_box = QComboBox()
        combo_box.ctrl_menu = ctrl_menu
        combo_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for menu_item in ctrl_menu.menu_list:
            combo_box.addItem(menu_item[1], menu_item[0])
        # Get the initial value of the combo box
        value = [item[1]
                 for item in ctrl_menu.key_value_list if item[0] == 'value'][0]
        # Find the index of the value in the menu list
        lookup = [idx for idx, element in enumerate(
            ctrl_menu.menu_list) if element[0] == value]
        if len(lookup) != 0:
            combo_box.setCurrentIndex(lookup[0])
        combo_box_menu_hbox.addWidget(combo_box)
        combo_box_menu_hbox.addStretch()
        combo_box.currentIndexChanged.connect(self.onComboBoxChanged)

        reset_button = QPushButton('Default')
        reset_button.ctrl_menu = ctrl_menu
        reset_button.combo_box = combo_box
        reset_button.clicked.connect(self.menu_reset_button_clicked)
        combo_box_menu_hbox.addWidget(reset_button)

        self.view.ctrl_dict[ctrl_menu.title] = [combo_box, reset_button]

        layout = self.view.control_menu_frame.layout()
        layout.addLayout(combo_box_menu_hbox)

    def setup_ctrl_menus(self, device_uri: str):
        layout = self.view.control_menu_frame.layout()
        self.view.clear_layout(layout)
        ctrl_menu_list = self.camera_inspector.get_ctrl_menus(device_uri)
        for ctrl_menu in ctrl_menu_list:
            try:
                ...  # print(ctrl_menu.menu_type)
            except:
                # FIXME - This try block needs work
                print(f"Ctrl_menu has no menu type: {ctrl_menu}")
                continue
            if 'int' == ctrl_menu.menu_type or 'int64' == ctrl_menu.menu_type:
                self.add_ctrl_slider(ctrl_menu)
            elif 'bool' == ctrl_menu.menu_type:
                self.add_ctrl_bool(ctrl_menu)
            elif 'menu' == ctrl_menu.menu_type or 'intmenu' == ctrl_menu.menu_type:
                self.add_ctrl_menu(ctrl_menu)
            else:
                # Unrecognized menu type
                print(
                    f"Unrecognized Menu type: {ctrl_menu.menu_type} named: {ctrl_menu.title}")
        layout = self.view.control_menu_frame.layout()
        layout.addStretch()
        self.set_control_enabled_states()

    def setup_camera_info(self, device_uri: str):
        # Get the camera info from the URI
        camera_info = self.get_camera(device_uri)
        if camera_info is None:
            self.view.bus_label.setText("No camera information available")
            self.view.driver_label.setText("")
            self.view.capabilities_label.setText("")
            self.view.device_capabilities_label.setText("")

        else:
            labelText = f"<font color='#0000ff'><b>{camera_info.camera_name}</b></font> is on bus: {camera_info.bus_address}"
            self.view.bus_label.setText(labelText)

            self.view.driver_label.setText(
                f"&nbsp;&nbsp;Driver: <font color='#0000ff'>{camera_info.driver_name}</font>  version: {camera_info.driver_version}")
            caps_list = ", ".join(camera_info.capabilities_list)
            self.view.capabilities_label.setText(
                f"  Capabilities: ({camera_info.capabilities_code}) {caps_list}")
            caps_list = ", ".join(camera_info.device_caps_list)
            self.view.device_capabilities_label.setText(
                f"  Device Capabilities:  ({camera_info.device_caps_code}) {caps_list}")

    def get_camera(self, device_uri):
        camera_info = None
        for camera in self.camera_list:
            for uri in camera.uri_list:
                if uri == device_uri:
                    camera_info = camera
                    break
            if camera_info is not None:
                break
        return camera_info

    def on_camera_box_changed(self, combo_box_index: int):
        # Switch Camera
        # Clear the pixel format, image size and fps lists
        self.view.pixel_format_list.clear()
        self.view.image_size_list.clear()
        self.view.fps_list.clear()
        self.camera_location = None
        self.camera_formats = None
        # The device uri is in the itemData of the combo box entry
        self.device_uri = self.view.camera_combo_box.itemData(combo_box_index)
        if self.device_uri is not None:
            self.camera_formats = self.camera_inspector.camera_formats(
                self.device_uri)
        if self.camera_formats is not None:
            for camera_format in self.camera_formats:
                format_name = f"{camera_format.pixel_format}"
                item = QListWidgetItem(format_name)
                item.camera_format = camera_format
                self.view.pixel_format_list.addItem(item)
        self.setup_camera_info(self.device_uri)
        video_settings = self.camera_inspector.get_camera_stream_settings(
            self.device_uri)

        # String is of the format: 'YUYV' (YUYV 4:2:2)
        try:
            fourcc = video_settings[0].split("'")[1]
        except Exception as exc:
            print(video_settings[0])
            print(exc)
        self.setup_gst_pipeline_source(fourcc)
        # setup the width, height, and frame rate

        self.setup_ctrl_menus(self.device_uri)
        # Set the current video pixel format, frame size, and frame duration

        pixel_format = video_settings[0]
        image_size = video_settings[1]
        image_size = image_size.replace("/", "x")
        frame_rate = video_settings[2]
        frame_rate = frame_rate.split(" ", maxsplit=1)[0]

        self.image_width, self.image_height = image_size.split('x')
        if frame_rate == '':
            frame_rate = '30'
        self.frame_rate = frame_rate.split('.')[0]
        # Construct gstreamer source pipelne
        preview_command = self.preview_command()
        self.view.line_edit.setText(preview_command)
        self.view.line_edit.setCursorPosition(0)

        self.setup_frame_format(pixel_format, image_size, frame_rate)
        # self.setup_frame_format(fourcc, image_size, frame_rate)

    def on_pixel_format_list_clicked(self, pixel_format: QListWidgetItem):
        self.view.image_size_list.clear()
        self.view.fps_list.clear()

        self.size_list = None
        camera_format = pixel_format.camera_format
        fourcc = camera_format.pixel_format.split("'")[1]
        self.setup_gst_pipeline_source(fourcc)

        self.size_list = camera_format.size_list
        for frame_size in camera_format.size_list:
            self.view.image_size_list.addItem(frame_size[0])
        if len(self.size_list) > 0:
            size_item_widget = self.view.image_size_list.item(0)
            size_item_widget.setSelected(True)
            self.view.image_size_list.scrollToItem(size_item_widget)
            self.on_image_size_list_clicked(size_item_widget)

    def setup_gst_pipeline_source(self, fourcc: str):
        camera = self.get_camera(self.device_uri)
        self.gst_source = ""
        self.gst_filters = ""
        self.fourcc = fourcc
        if camera.driver_name == 'tegra-camrtc-ca':
            sensor_id = self.device_uri.lstrip('/dev/video')
            self.gst_source = f"nvarguscamerasrc sensor-id={sensor_id}"
            self.gst_filters = "video/x-raw(memory:NVMM), width={}, height={}, framerate={}/1 ! nvvidconv ! xvimagesink"
            self.fourcc = 'NVMM'
        elif camera.driver_name == 'uvcvideo':
            self.gst_source = f"v4l2src device={self.device_uri}"
            try:
                self.gst_filters = Command_Map.filters[fourcc]
            except KeyError:
                print(f"Unsupported format: {fourcc}")
                self.gst_filters = ""
        else:
            print("Unknown camera driver type")

    def on_image_size_list_clicked(self, image_size: QListWidgetItem):
        self.view.fps_list.clear()
        image_size_text = image_size.text()
        image_size_text = image_size_text.lstrip('Discrete ')
        self.image_width, self.image_height = image_size_text.split('x')
        if self.camera_formats is not None:
            if self.size_list is not None:
                for frame_size in self.size_list:
                    if frame_size[0] == image_size.text():
                        for fps in frame_size[1:]:
                            self.view.fps_list.addItem(fps)
                        # Select the first item in the fps list
                        if len(frame_size[1:]) > 0:
                            fps_widget = self.view.fps_list.item(0)
                            fps_widget.setSelected(True)
                            self.view.fps_list.scrollToItem(fps_widget)
                            self.on_fps_list_clicked(fps_widget)
                        break
            else:
                # TODO Throw Exception
                print("camera_formats not set correctly")

        else:
            # TODO Throw Exception
            print("camera_formats not set correctly")

    def setup_frame_format(self, pixel_format, image_size, frame_rate):
        list_widget = self.view.pixel_format_list
        count = list_widget.count()
        count -= 1
        while count >= 0:
            list_widget_item: QListWidgetItem = list_widget.item(count)
            camera_format: Camera_Format = list_widget_item.camera_format
            camera_pixel_format = camera_format.pixel_format.split(" ")[0]
            if camera_pixel_format == pixel_format:
                list_widget_item.setSelected(True)
                list_widget.scrollToItem(list_widget_item)
                # Populate Image Sizes
                self.view.image_size_list.clear()
                self.size_list = None
                self.size_list = camera_format.size_list
                for frame_size in camera_format.size_list:
                    frame_size_text = frame_size[0]
                    frame_size_widget_item = QListWidgetItem(frame_size_text)
                    self.view.image_size_list.addItem(frame_size_widget_item)
                    if image_size in frame_size_text:
                        frame_size_widget_item.setSelected(True)
                        self.view.image_size_list.scrollToItem(
                            frame_size_widget_item)
                        # Populate Frame Rate
                        fps_list = self.view.fps_list
                        fps_list.clear()
                        for frame_size in self.size_list:
                            if image_size in frame_size[0]:
                                for fps in frame_size[1:]:
                                    fps_list_widget = QListWidgetItem(fps)
                                    fps_list.addItem(fps_list_widget)
                                    if frame_rate != "" and frame_rate in fps:
                                        fps_list_widget.setSelected(True)
                                        fps_list.scrollToItem(fps_list_widget)
            count -= 1

    def check_box_onClicked(self):
        check_box = self.view.sender()
        ctrl_menu = check_box.ctrl_menu
        if check_box.isChecked():
            self.set_ctl_value(ctrl_menu.title, 1)
        else:
            self.set_ctl_value(ctrl_menu.title, 0)
        self.set_control_enabled_states()

    def onSliderValueChanged(self, value):
        slider = self.view.sender()
        ctrl_menu = slider.ctrl_menu
        spin_box = slider.spin_box
        spin_box.setValue(value)
        self.set_ctl_value(ctrl_menu.title, value)
        if slider.default_value != value:
            slider.reset_button.setEnabled(True)
        else:
            slider.reset_button.setEnabled(False)

    def onSpinBoxValueChanged(self, value):
        spin_box = self.view.sender()
        slider = spin_box.slider
        slider.setValue(value)

    def onComboBoxChanged(self, index):
        combo_box = self.view.sender()
        ctrl_menu = combo_box.ctrl_menu
        menu_entry = ctrl_menu.menu_list[index]
        self.set_ctl_value(ctrl_menu.title, int(menu_entry[0]))
        self.set_control_enabled_states()

    def slider_reset_button_clicked(self):
        button = self.view.sender()
        ctrl_menu = button.ctrl_menu
        # Get the default value
        default_value = [item[1]
                         for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
        if default_value is not None:
            button.slider.setValue(int(default_value))
            # self.set_ctl_value(ctrl_menu.title,int(default_value))
            # Need to update the slider

        else:
            # TODO Notify user
            print(f"Unable to find default value for: {ctrl_menu.title}")

    def bool_reset_button_clicked(self):
        bool_ctrl = self.view.sender()
        ctrl_menu = bool_ctrl.ctrl_menu
        value = [item[1]
                 for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
        if value == '1':
            bool_ctrl.check_box.setChecked(True)
        else:
            bool_ctrl.check_box.setChecked(False)
        self.set_control_enabled_states()

    def menu_reset_button_clicked(self):
        menu_reset = self.view.sender()
        ctrl_menu = menu_reset.ctrl_menu
        combo_box = menu_reset.combo_box
        # Get the default value of the combo box
        value = [item[1]
                 for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
        # Find the index of the value in the menu list
        lookup = [idx for idx, element in enumerate(
            ctrl_menu.menu_list) if element[0] == value]
        if len(lookup) != 0:
            combo_box.setCurrentIndex(lookup[0])
        self.set_control_enabled_states()

    def preview_button_clicked(self):
        preview_button = self.view.sender()
        line_edit = preview_button.line_edit
        command_line = line_edit.text()
        # Get the preview window for this camera
        preview_window: PreviewWindow = [
            window for window in self.view.preview_windows if window.device_uri == self.device_uri]
        if len(preview_window) is None:
            print(f"Unable to find preview window for {self.device_uri}")
        else:
            preview_window = preview_window[0]

        if preview_window is not None:
            # If camera is currently running, stop it
            if preview_window.video_widget.has_video():
                preview_window.video_widget.close_pipeline()
            # Setup for new pipeline, start it, and show the window
            preview_window.video_widget.setup_pipeline(command_line)
            preview_window.video_widget.start_pipeline()
            # Show the window and bring it to front
            window_title = f"{preview_window.base_title} - '{self.fourcc}' {self.image_width}x{self.image_height}"
            preview_window.setWindowTitle(window_title)
            preview_window.show()
            preview_window.activateWindow()
            preview_window.raise_()
        return

    def copy_button_clicked(self):
        clipboard = QApplication.clipboard()
        copy_button = self.view.sender()
        line_edit = copy_button.line_edit
        command_line = line_edit.text()
        # Try to make this a valid gst-launch command - not guaranteed to work
        split_command = command_line.split('!')
        quoted_command = []
        for cmd in split_command:
            if '(' in cmd:
                cmd = f" '{cmd.strip()}' "
            quoted_command.append(cmd)
        quoted_command = "!".join(quoted_command)

        # We add gst-launch to the command line
        gst_launch_str = "gst-launch-1.0 " + quoted_command
        print(gst_launch_str)
        clipboard.setText(gst_launch_str)

    """ Changing the state of one control might change the state of other associated controls.
        Get the control menu list, and mark the ctrls as enabled or inactive as noted in the
        ctrl menu list. This does *NOT* take into account any dynamic menus which may be added
        or subtracted by state change, that is, only existing ctrls are set """

    def set_control_enabled_states(self):
        inactive_list = self.camera_inspector.get_inactive_ctrls(
            self.device_uri)
        for key, value in self.view.ctrl_dict.items():
            active_flag = True
            if key in inactive_list:
                active_flag = False
            for ctrl in value:
                ctrl.setEnabled(active_flag)
        # Make the 'default' button enabled/disabled
        for key, value in self.view.ctrl_dict.items():
            # Get the reset button, it should be the last control in the list
            reset_button = value[-1]
            if not key in inactive_list:
                reset_button.setEnabled(self.is_default_value(reset_button))

    """ Is the control associated with this reset button the default value?"""

    def is_default_value(self, reset_button):
        to_return = True
        ctrl_menu = reset_button.ctrl_menu
        if 'int' == ctrl_menu.menu_type or 'int64' == ctrl_menu.menu_type:
            # Slider
            default_value = [
                item[1] for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
            if default_value is not None:
                current_value = reset_button.slider.value()
                to_return = not (current_value == int(default_value))
        elif 'bool' == ctrl_menu.menu_type:
            # Check Box
            default_value = [item[1]
                             for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
            if default_value == '1' and reset_button.check_box.isChecked() == True:
                to_return = False
            elif default_value == '0' and reset_button.check_box.isChecked() == False:
                to_return = False
        elif 'menu' == ctrl_menu.menu_type or 'intmenu' == ctrl_menu.menu_type:
            # Combo Box
            default_value = [item[1]
                             for item in ctrl_menu.key_value_list if item[0] == 'default'][0]
            # Find the index of the value in the menu list
            lookup = [idx for idx, element in enumerate(
                ctrl_menu.menu_list) if element[0] == default_value]
            if len(lookup) != 0:
                if lookup[0] == reset_button.combo_box.currentIndex():
                    to_return = False
        else:
            # Unrecognized menu type
            print(
                f"Unrecognized Defautl Menu type: {ctrl_menu.menu_type} named: {ctrl_menu.title}")
        return to_return

    def on_fps_list_clicked(self, fps: QListWidgetItem):
        fps_text = fps.text()
        fps_text = fps_text.split("(")[1]
        fps_text = fps_text.split(".")[0]
        self.frame_rate = fps_text
        # Construct gstreamer
        preview_command = self.preview_command()
        self.view.line_edit.setText(preview_command)

    def preview_command(self):
        gst_filters = self.gst_filters.format(
            self.image_width, self.image_height, self.frame_rate)
        preview_command = f"{self.gst_source} ! {gst_filters}"
        return preview_command

    def app_quitting(self):
        """ The application is quitting, close any camera preview windows"""
        """ This is handled in the main script """
        pass

