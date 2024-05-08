from dataclasses import dataclass, replace

@dataclass
class CameraSettings:
    image_width: str = ""   # Currently selected image width
    image_height: str = ""  # Currently selected image height
    frame_rate: str = "30"  # Currently selected frame rate
    fourcc: str = ""        # Currently selected fourcc, e.g. YUY2
    media_type: str = ""    # E.g. image/jpeg

def generate_capsfilter_string(settings: CameraSettings) -> str:
    properties = {
        "media_type": "",
        "image_width": "width",
        "image_height": "height",
        "frame_rate": "framerate",
        "fourcc": "format"
    }

    caps_string = ", ".join(f"{prop}={getattr(settings, attr)}" for attr, prop in properties.items() if getattr(settings, attr))
    return caps_string