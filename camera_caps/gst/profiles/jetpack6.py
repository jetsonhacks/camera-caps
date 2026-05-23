from camera_caps.gst.pipeline_builder import GstFormatProfile, GstPipelineProfile


PROFILE = GstPipelineProfile(
    name="jetpack6",
    tegra_filter=(
        "video/x-raw(memory:NVMM), width={}, height={}, framerate={}/1 "
        "! nvvidconv ! xvimagesink"
    ),
    uvc_formats={
        "YUYV": GstFormatProfile(
            media_type="video/x-raw",
            format_name="YUY2",
            decoder="",
            sink="xvimagesink sync={}",
            crop_decoder=(
                "! videocrop name=cropper ! videoscale ! video/x-raw, "
                "width={}, height={} ! videoconvert "
            ),
        ),
        "H264": GstFormatProfile(
            media_type="video/x-h264",
            format_name="H264",
            decoder="! h264parse ! avdec_h264  ",
            sink="xvimagesink sync={}",
            crop_decoder="! h264parse ! avdec_h264  ! videocrop name=cropper ",
        ),
        "MJPG": GstFormatProfile(
            media_type="image/jpeg",
            format_name="MJPG",
            decoder="! nvv4l2decoder mjpeg=1 ! nvvidconv ",
            sink="xvimagesink sync={}",
            crop_decoder="! nvv4l2decoder mjpeg=1 ! nvvidconv ! videocrop name=cropper ",
        ),
        "UYVY": GstFormatProfile(
            media_type="video/x-raw",
            format_name="UYVY",
            decoder="",
            sink="xvimagesink sync={}",
            crop_decoder=(
                "! videocrop name=cropper ! videoscale ! video/x-raw, "
                "width={}, height={} ! videoconvert "
            ),
        ),
    },
)
