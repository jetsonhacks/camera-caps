import unittest

from camera_caps.gst.pipeline_builder import GstPipelineBuilder
from camera_caps.gst.profiles import generic, jetpack6


class GstPipelineBuilderTest(unittest.TestCase):
    def test_jetpack6_mjpeg_preview_pipeline_preserves_known_good_elements(self):
        builder = GstPipelineBuilder(jetpack6.PROFILE)
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertEqual(
            command,
            "v4l2src device=/dev/video0 ! "
            "image/jpeg, width=3840, height=2592, framerate=30/1, format=MJPG "
            "! nvv4l2decoder mjpeg=1 ! nvvidconv ! videocrop name=cropper  "
            "! xvimagesink sync=false",
        )
        self.assertIn("v4l2src device=/dev/video0", command)
        self.assertIn("image/jpeg", command)
        self.assertIn("nvv4l2decoder mjpeg=1", command)
        self.assertIn("nvvidconv", command)
        self.assertIn("videocrop name=cropper", command)
        self.assertIn("xvimagesink sync=false", command)

    def test_sync_property_values_are_lowercase(self):
        builder = GstPipelineBuilder(jetpack6.PROFILE)
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        false_command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )
        true_command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=True,
        )

        self.assertIn("xvimagesink sync=false", false_command)
        self.assertIn("xvimagesink sync=true", true_command)

    def test_generic_fallback_mjpeg_profile_uses_portable_decoder(self):
        builder = GstPipelineBuilder(generic.PROFILE)
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="640",
            height="480",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("v4l2src device=/dev/video0", command)
        self.assertIn("image/jpeg", command)
        self.assertIn("jpegdec", command)
        self.assertIn("videocrop name=cropper", command)


if __name__ == "__main__":
    unittest.main()
