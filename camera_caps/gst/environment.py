import os
import re
import subprocess

from camera_caps.gst.profiles import generic, jetpack6, jetpack7


GI_INSTALL_HINT = (
    "PyGObject/GStreamer Python bindings are not installed. "
    "Install the system packages with: sudo apt install python3-gi "
    "gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0"
)


def default_profile():
    profile_name = os.environ.get("CAMERA_CAPS_GST_PROFILE", "").lower()
    if profile_name == "jetpack7":
        return jetpack7.PROFILE
    if profile_name == "jetpack6":
        return jetpack6.PROFILE
    if profile_name == "generic":
        return generic.PROFILE

    if detect_jetpack_major() == 7:
        return jetpack7.PROFILE

    return jetpack6.PROFILE


def fallback_profile():
    return generic.PROFILE


def detect_jetpack_major(release_text: str = None):
    if release_text is None:
        try:
            with open("/etc/nv_tegra_release", encoding="utf-8") as release_file:
                release_text = release_file.read()
        except OSError:
            return None

    match = re.search(r"\bR(\d+)", release_text)
    if match is None:
        return None

    l4t_major = int(match.group(1))
    if l4t_major >= 38:
        return 7
    if l4t_major >= 36:
        return 6
    return None


def gst_element_available(element_name: str) -> bool:
    try:
        subprocess.run(
            ["gst-inspect-1.0", element_name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False
    return True


def gst_element_property_available(element_name: str, property_name: str) -> bool:
    try:
        result = subprocess.run(
            ["gst-inspect-1.0", element_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
        )
    except Exception:
        return False
    return property_name in result.stdout


def import_gst():
    try:
        import gi
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(GI_INSTALL_HINT) from exc

    gi.require_version("Gst", "1.0")
    gi.require_version("GstVideo", "1.0")

    try:
        from gi.repository import Gst, GstVideo
    except (ImportError, ValueError) as exc:
        raise ImportError(GI_INSTALL_HINT) from exc

    return Gst, GstVideo
