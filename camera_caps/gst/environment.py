from camera_caps.gst.profiles import generic, jetpack6


GI_INSTALL_HINT = (
    "PyGObject/GStreamer Python bindings are not installed. "
    "Install the system packages with: sudo apt install python3-gi "
    "gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0"
)


def default_profile():
    return jetpack6.PROFILE


def fallback_profile():
    return generic.PROFILE


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
