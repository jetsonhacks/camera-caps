from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple, Union


@dataclass(frozen=True)
class GstFormatProfile:
    media_type: str
    format_name: str
    decoder: str
    sink: str
    crop_decoder: str
    required_elements: Sequence[str] = ()
    required_properties: Sequence[Tuple[str, str]] = ()
    source_properties: str = ""


@dataclass(frozen=True)
class GstPipelineProfile:
    name: str
    uvc_formats: Dict[str, Union[GstFormatProfile, Sequence[GstFormatProfile]]]
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
    def __init__(
        self,
        profile=None,
        element_available: Callable[[str], bool] = None,
        property_available: Callable[[str, str], bool] = None,
    ):
        if profile is None:
            from camera_caps.gst.environment import default_profile

            profile = default_profile()
        if element_available is None:
            from camera_caps.gst.environment import gst_element_available

            element_available = gst_element_available
        if property_available is None:
            from camera_caps.gst.environment import gst_element_property_available

            property_available = gst_element_property_available
        self.profile = profile
        self.element_available = element_available
        self.property_available = property_available

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
            format_profile = self._select_format_profile(fourcc)
            source = f"v4l2src device={device_uri}"
            if format_profile.source_properties:
                source = f"{source} {format_profile.source_properties}"

            return GstPipelineTemplate(
                source=source,
                filters=self._format_filter(format_profile.decoder, format_profile),
                crop_filters=self._format_filter(
                    format_profile.crop_decoder, format_profile
                ),
                media_type=format_profile.media_type,
                fourcc=fourcc,
            )

        raise ValueError(f"Unknown camera driver type: {driver_name}")

    def _select_format_profile(self, fourcc: str) -> GstFormatProfile:
        try:
            format_profiles = self.profile.uvc_formats[fourcc]
        except KeyError:
            raise ValueError(f"Unsupported format: {fourcc}")

        if isinstance(format_profiles, GstFormatProfile):
            candidates: List[GstFormatProfile] = [format_profiles]
        else:
            candidates = list(format_profiles)

        for format_profile in candidates:
            if all(
                self.element_available(element)
                for element in format_profile.required_elements
            ) and all(
                self.property_available(element, prop)
                for element, prop in format_profile.required_properties
            ):
                return format_profile

        raise ValueError(f"No available pipeline candidate for format: {fourcc}")

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
