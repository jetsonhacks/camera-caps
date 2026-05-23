from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class GstFormatProfile:
    media_type: str
    format_name: str
    decoder: str
    sink: str
    crop_decoder: str


@dataclass(frozen=True)
class GstPipelineProfile:
    name: str
    uvc_formats: Dict[str, GstFormatProfile]
    tegra_filter: str
    tegra_media_type: str = "video/x-raw(memory:NVMM)"
    tegra_fourcc: str = "NVMM"


@dataclass(frozen=True)
class GstPipelineTemplate:
    source: str
    filters: str
    crop_filters: str
    media_type: str
    fourcc: str


COMMAND_BASE = "{}, width={}, height={}, framerate={}/1, format={} {} ! {}"


class GstPipelineBuilder:
    def __init__(self, profile=None):
        if profile is None:
            from camera_caps.gst.environment import default_profile

            profile = default_profile()
        self.profile = profile

    def build_template(
        self, driver_name: str, device_uri: str, fourcc: str
    ) -> GstPipelineTemplate:
        if driver_name == "tegra-camrtc-ca":
            sensor_id = device_uri.lstrip("/dev/video")
            return GstPipelineTemplate(
                source=f"nvarguscamerasrc sensor-id={sensor_id}",
                filters=self.profile.tegra_filter,
                crop_filters=self.profile.tegra_filter,
                media_type=self.profile.tegra_media_type,
                fourcc=self.profile.tegra_fourcc,
            )

        if driver_name == "uvcvideo":
            try:
                format_profile = self.profile.uvc_formats[fourcc]
            except KeyError:
                raise ValueError(f"Unsupported format: {fourcc}")

            return GstPipelineTemplate(
                source=f"v4l2src device={device_uri}",
                filters=self._format_filter(format_profile.decoder, format_profile),
                crop_filters=self._format_filter(
                    format_profile.crop_decoder, format_profile
                ),
                media_type=format_profile.media_type,
                fourcc=fourcc,
            )

        raise ValueError(f"Unknown camera driver type: {driver_name}")

    def build_preview_command(
        self,
        template: GstPipelineTemplate,
        width: str,
        height: str,
        frame_rate: str,
        sync: bool,
        use_crop: bool = True,
    ) -> str:
        filters = template.crop_filters if use_crop else template.filters
        sync_value = str(sync).lower()
        if use_crop and template.fourcc in ("YUY2", "YUYV"):
            filters = filters.format(
                width, height, frame_rate, width, height, sync_value
            )
        else:
            filters = filters.format(width, height, frame_rate, sync_value)
        return f"{template.source} ! {filters}"

    def _format_filter(self, decoder: str, format_profile: GstFormatProfile) -> str:
        return COMMAND_BASE.format(
            format_profile.media_type,
            "{}",
            "{}",
            "{}",
            format_profile.format_name,
            decoder,
            format_profile.sink,
        )
