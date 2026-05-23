from camera_caps.gst.pipeline_builder import GstFormatProfile, GstPipelineProfile


# JetPack 7 / Jetson Linux 38 UVC MJPEG preview path:
# Force V4L2 MMAP capture and source-side timestamps. Leaving io-mode at
# auto produced high-latency, low-framerate preview on Reachy Mini's UVC
# MJPEG camera with the nvjpegdec -> nv3dsink path.
UVC_MJPEG_SOURCE_PROPERTIES = "io-mode=2 do-timestamp=true"
UVC_MJPEG_NVJPEG_DECODER = (
    "! jpegparse ! nvjpegdec ! "
    "video/x-raw(memory:NVMM), format=Y42B ! nvvidconv ! "
    "video/x-raw(memory:NVMM), format=NV12 "
)
UVC_MJPEG_NVJPEG_CROP_DECODER = (
    "! jpegparse ! nvjpegdec ! "
    "video/x-raw(memory:NVMM), format=Y42B ! nvvidconv ! "
    "video/x-raw(memory:NVMM), format=NV12 ! "
    "videocrop name=cropper "
)


PROFILE = GstPipelineProfile(
    name="jetpack7",
    tegra_filter=(
        "video/x-raw(memory:NVMM), width={}, height={}, framerate={}/1 "
        "! nvvidconv ! nv3dsink"
    ),
    uvc_formats={
        "MJPG": (
            GstFormatProfile(
                media_type="image/jpeg",
                format_name="MJPG",
                decoder=UVC_MJPEG_NVJPEG_DECODER,
                sink="nveglglessink force-aspect-ratio=true sync={}",
                crop_decoder=UVC_MJPEG_NVJPEG_CROP_DECODER,
                required_elements=("nvjpegdec", "nveglglessink"),
                required_properties=(("nveglglessink", "force-aspect-ratio"),),
                source_properties=UVC_MJPEG_SOURCE_PROPERTIES,
            ),
            GstFormatProfile(
                media_type="image/jpeg",
                format_name="MJPG",
                decoder=UVC_MJPEG_NVJPEG_DECODER,
                sink="nveglglessink sync={}",
                crop_decoder=UVC_MJPEG_NVJPEG_CROP_DECODER,
                required_elements=("nvjpegdec", "nveglglessink"),
                source_properties=UVC_MJPEG_SOURCE_PROPERTIES,
            ),
            GstFormatProfile(
                media_type="image/jpeg",
                format_name="MJPG",
                decoder=UVC_MJPEG_NVJPEG_DECODER,
                sink="nv3dsink sync={}",
                crop_decoder=UVC_MJPEG_NVJPEG_CROP_DECODER,
                required_elements=("nvjpegdec", "nv3dsink"),
                source_properties=UVC_MJPEG_SOURCE_PROPERTIES,
            ),
            GstFormatProfile(
                media_type="image/jpeg",
                format_name="MJPG",
                decoder="! jpegparse ! jpegdec ! videoconvert ",
                sink="xvimagesink sync={}",
                crop_decoder=(
                    "! jpegparse ! jpegdec ! videoconvert ! "
                    "videocrop name=cropper "
                ),
                source_properties=UVC_MJPEG_SOURCE_PROPERTIES,
            ),
        )
    },
)
