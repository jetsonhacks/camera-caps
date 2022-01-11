#
#  Camera Capabilities
#
#  Copyright (C) 2021 JetsonHacks (info@jetsonhacks.com)
#
#  MIT License
#
import subprocess
import re

from typing import ClassVar, List
from dataclasses import dataclass, field


@dataclass
class Camera_Preview:
    process: subprocess = None # This is reall a subprocess
    device_id: str = ""


@dataclass
class Camera_Info:
    camera_name: str = ""
    bus_address: str = ""
    # Some cameras have multiple uris, such as depth cameras
    uri_list: list = field(default_factory=list)
    ctrl_menu_list: list = field(default_factory=list)
    driver_name: str = ""
    driver_version: str = ""
    capabilities_code: str = ""
    capabilities_list: str = ""
    device_caps_code: str = ""
    device_caps_list: str = ""


@dataclass
class Control_Menu_Entry:
    title: str = ""
    address: str = ""
    menu_type: str = ""
    key_value_list: list = field(default_factory=list)
    flags_list: list = field(default_factory=list)
    menu_list: list = field(default_factory=list)


@dataclass
class Camera_Format:

    attr_names: ClassVar = {'Index': 'index', 'Type': 'type',
                            'Pixel Format': 'pixel_format', 'Name': 'format_name'}
    size_names: ClassVar = {'Size': 'size', 'Interval': 'interval'}

    index: str = ""
    type: str = ""
    pixel_format: str = ""
    format_name: str = ""
    size_list: list = field(default_factory=list)

    def set_attribute(self, key: str, value: str) -> None:
        attr_name = None
        try:
            attr_name = self.attr_names[key]
            if (attr_name is not None):
                setattr(self, attr_name, value)
            else:
                print("set_attribute has bad attr_name")
                # TODO Throw exception here
        except KeyError:
            try:
                size_name = self.size_names[key]
                if size_name == 'size':
                    self.size_list.append([value])
                elif size_name == 'interval':
                    self.size_list[-1].append(value)
                else:
                    print('Bad size_name')
            except KeyError:
                # TODO Throw exception here
                print(f"Could not find key: {key}")


class Camera_Inspector:

    """ Return a list of cameras
    Example: v4l2-ctl --list-devices returns entries in the format:
    HD Pro Webcam C920 (usb-3610000.xhci-2.3):
        /dev/video0

    Some devices have multiple uris, such as depth cameras
    """

    def get_control_list_menus(self, uri: str):
        try:
            to_return = subprocess.check_output(
                ["v4l2-ctl", "-d", uri, "--list-ctrls-menus"], encoding='utf-8')
        except Exception as exc:
            print(exc)
            to_return = None
        return to_return

    def list_cameras(self) -> List:
        """ Return a list of cameras, if any"""
        to_return = []
        try:
            list_devices = subprocess.check_output(
                ["v4l2-ctl", "--list-devices"], encoding='utf-8')
        except Exception as exc:
            print(exc)
            list_devices = None
        if list_devices is not None:
            camera = None
            # For example: HD Pro Webcam C920 (usb-3610000.xhci-2.1.3.1):
            #	                /dev/video0
            for line in list_devices.splitlines():
                if len(line) == 0:
                    continue
                if line.rfind("):") != -1:
                    bus_index = line.rfind('(')
                    camera_name = line[0:bus_index]
                    bus_address = line[bus_index+1:(len(line)-2)]
                    camera = Camera_Info(camera_name.rstrip(), bus_address)
                    to_return.append(camera)
                else:
                    uri_string = line.lstrip()
                    camera.uri_list.append(uri_string)
                    ctrl_list_menus = self.get_control_list_menus(uri_string)
                    camera.ctrl_menu_list.append(ctrl_list_menus)
        # Get the extended info for each camera
        for camera in to_return:
            self.get_camera_info(camera)

        return to_return

    def get_camera_info(self, camera: Camera_Info):
        try:
            # We use the first uri in the camera list to get the device info
            # That may be incorrect, cameras that have multiple URIs (like depth cameras)
            # may have different info for each stream ...
            uri = camera.uri_list[0]
            if uri is None:
                print(f"Unable to find camera device URI: {camera.title}")
                return
            camera_info = subprocess.check_output(
                ["v4l2-ctl", "--info", "-d", uri], encoding='utf-8')
        except Exception as exc:
            # TODO Propogate Exception
            print(f"Unable to get device info: {exc}")
        # Parse everything into a dictionary
        info_dict = {'capabilities_list': [], 'device_caps_list': []}
        for line in camera_info.splitlines():
            if len(line) == 0:
                continue
            try:
                key, value = line.split(':', maxsplit=1)
                info_dict[key.strip()] = value.strip()
            except ValueError:
                # This is a capability; key indicates Regular or Device Caps
                if key.strip() == 'Capabilities':
                    info_dict['capabilities_list'].append(line.strip())
                elif key.strip() == 'Device Caps':
                    info_dict['device_caps_list'].append(line.strip())
                else:
                    print(f"Unknown line: {line}")
        try:
            camera.driver_name = info_dict['Driver name']
            camera.driver_version = info_dict['Driver version']
            camera.capabilities_code = info_dict['Capabilities']
            camera.capabilities_list = info_dict['capabilities_list']
            camera.device_caps_code = info_dict['Device Caps']
            camera.device_caps_list = info_dict['device_caps_list']
        except Exception as exc:
            # TODO
            print(f"Issue with setting device info: {exc}")

    def camera_formats(self, device_uri: str):
        """ Return the camera formats"""
        to_return = []
        try:
            formats = subprocess.check_output(
                ["v4l2-ctl", "--list-formats-ext", "-d", device_uri], encoding='utf-8')
        except Exception as exc:
            print(exc)
            formats = None

        if formats is not None:
            camera_format = None
            for line in formats.splitlines():
                if len(line) == 0:
                    continue
                # camera = None
                key, value = line.split(':', maxsplit=1)
                key = key.strip()
                value = value.strip()
                # print(f"Key: {key} : Value: {value}")
                if key == 'Index':
                    camera_format = Camera_Format()
                    to_return.append(camera_format)
                if camera_format is not None:
                    camera_format.set_attribute(key, value)

        return to_return

    def get_inactive_ctrls(self, device_uri: str) -> list:
        ctrl_menus = self.get_control_list_menus(device_uri)
        inactive_ctrl_list = []
        if ctrl_menus is not None:
            in_menu = False  # Parsing a menu entry?
            ctrl_menu_entry = None
            for line in ctrl_menus.splitlines():
                if len(line) == 0:
                    in_menu = False
                    continue
                elif line.startswith("Camera Controls"):
                    in_menu = False
                    continue
                elif line.startswith("User Controls"):
                    in_menu = False
                    continue
                if in_menu:
                    # Does this line fit the profile?
                    # decimal : string or decimal : decimal (hex)
                    to_test = line.split(':')
                    if to_test[0].strip().isdecimal():
                        ctrl_menu_entry.menu_list.append(
                            [to_test[0].strip(), to_test[1].strip()])
                        continue
                    else:
                        # Done parsing the menu entries
                        in_menu = False
                # Get the title
                if 'flags=inactive' in line:
                    title = (line.split("0x")[0]).strip()
                    inactive_ctrl_list.append(title)

        return inactive_ctrl_list

    def get_ctrl_menus(self, device_uri: str) -> list:
        ctrl_menus = self.get_control_list_menus(device_uri)
        ctrl_menu_entry_list = []
        if ctrl_menus is not None:
            in_menu = False   # Parsing a menu entry?
            ctrl_menu_entry = None
            for line in ctrl_menus.splitlines():

                if len(line) == 0:
                    in_menu = False
                    continue
                elif line.startswith("Camera Controls"):
                    in_menu = False
                    continue
                elif line.startswith("User Controls"):
                    in_menu = False
                    continue

                if in_menu:
                    # Does this line fit the profile?
                    # decimal : string or decimal : decimal (hex)
                    to_test = line.split(':')
                    if to_test[0].strip().isdecimal():
                        ctrl_menu_entry.menu_list.append(
                            [to_test[0].strip(), to_test[1].strip()])
                        continue
                    else:
                        # Done parsing the menu entries
                        in_menu = False

                ctrl_menu_entry = Control_Menu_Entry()
                ctrl_menu_entry_list.append(ctrl_menu_entry)
                # Get the title
                ctrl_menu_entry.title = (line.split("0x")[0]).strip()
                # Get the menu type
                try:
                    ctrl_menu_entry.menu_type = re.search(
                        r'\((.*?)\)', line).group(1)
                except:
                    pass
                if 'menu' in ctrl_menu_entry.menu_type:
                    in_menu = True

                # get the ioctl address; it's in hex 0xXXXXX
                try:
                    ctrl_menu_entry.address = re.search(
                        r'0x([0-9a-fA-F]+)\s*', line).group(1)
                except:
                    pass
                # Get the key=value pairs
                vals = re.findall(r'([^\s|:]+)=\s*([^\s|:]+)', line)
                ctrl_menu_entry.key_value_list = vals
                # Get the flags at the end of the line, CSV names
                flags = line.split(',')
                if len(flags) > 1:
                    del flags[0]
                else:
                    flags = []
                ctrl_menu_entry.flags_list = flags
                # print(line)
            # print("-------------------------------------------")
            # print(ctrl_menu_entry_list)
            # print("-------------------------------------------")
        return ctrl_menu_entry_list

    def get_camera_all(self, device_uri: str):
        camera_info = ""
        try:
            camera_info = subprocess.check_output(
                ["v4l2-ctl", "--all", "-d", device_uri], encoding='utf-8')
        except Exception as exc:
            # TODO Propogate Exception
            print(f"Unable to get device info: {exc}")
        return camera_info

    def get_camera_stream_settings(self, device_uri: str):
        pixel_format = ""
        image_size = ""
        frame_rate = ""
        camera_info = self.get_camera_all(device_uri)

        for line in camera_info.splitlines():
            key = line.split(":", maxsplit=1)
            title = key[0].strip()
            if title == 'Width/Height':
                image_size = key[1].strip()
                continue
            if title == 'Pixel Format':
                pixel_format = key[1].strip()
                continue
            if title == 'Frames per second':
                frame_rate = key[1].strip()
        to_return = [pixel_format, image_size, frame_rate]
        return to_return


""" 
def main():
    camera_inspector = Camera_Inspector()
    camera_list = camera_inspector.list_cameras()
    print(camera_list)
    camera_formats = camera_inspector.camera_formats("/dev/video1")
    for format in camera_formats:
        print(format)
    # print(camera_formats)


if __name__ == '__main__':
    main()

"""
