from camera_caps.gst.pipeline_builder import GstFormatProfile, GstPipelineProfile


PROFILE = GstPipelineProfile(
    name="generic",
    tegra_filter="video/x-raw, width={}, height={}, framerate={}/1 ! xvimagesink",
    tegra_media_type="video/x-raw",
    tegra_fourcc="RAW",
    uvc_formats={
        "YUYV": GstFormatProfile(
            media_type="video/x-raw",
            format_name="YUY2",
            decoder="",
            sink="xvimagesink sync={}",
            crop_decoder="! videocrop name=cropper ! videoconvert ",
        ),
        "MJPG": GstFormatProfile(
            media_type="image/jpeg",
            format_name="MJPG",
            decoder="! jpegdec ! videoconvert ",
            sink="xvimagesink sync={}",
            crop_decoder="! jpegdec ! videoconvert ! videocrop name=cropper ",
        ),
    },
)
