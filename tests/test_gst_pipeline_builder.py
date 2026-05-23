import unittest

from camera_caps.gst.pipeline_builder import GstPipelineBuilder
from camera_caps.gst.profiles import generic, jetpack6, jetpack7


class GstPipelineBuilderTest(unittest.TestCase):
    def element_available(self, available_elements):
        return lambda element: element in available_elements

    def property_available(self, available_properties):
        return lambda element, prop: (element, prop) in available_properties

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
        self.assertNotIn("io-mode=2", command)
        self.assertNotIn("do-timestamp=true", command)

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

    def test_jetpack7_mjpeg_uses_nvjpegdec_when_available(self):
        builder = GstPipelineBuilder(
            jetpack7.PROFILE,
            element_available=self.element_available(
                {"nvjpegdec", "nveglglessink"}
            ),
            property_available=self.property_available(set()),
        )
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("jpegparse", command)
        self.assertIn("nvjpegdec", command)
        self.assertIn("nveglglessink sync=false", command)
        self.assertIn("io-mode=2", command)
        self.assertIn("do-timestamp=true", command)

    def test_jetpack7_mjpeg_uses_force_aspect_ratio_when_supported(self):
        builder = GstPipelineBuilder(
            jetpack7.PROFILE,
            element_available=self.element_available(
                {"nvjpegdec", "nveglglessink"}
            ),
            property_available=self.property_available(
                {("nveglglessink", "force-aspect-ratio")}
            ),
        )
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("nveglglessink force-aspect-ratio=true sync=false", command)

    def test_jetpack7_mjpeg_omits_force_aspect_ratio_when_unsupported(self):
        builder = GstPipelineBuilder(
            jetpack7.PROFILE,
            element_available=self.element_available(
                {"nvjpegdec", "nveglglessink"}
            ),
            property_available=self.property_available(set()),
        )
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("nveglglessink sync=false", command)
        self.assertNotIn("force-aspect-ratio=true", command)

    def test_jetpack7_mjpeg_falls_back_to_nv3dsink_when_nveglglessink_unavailable(self):
        builder = GstPipelineBuilder(
            jetpack7.PROFILE,
            element_available=self.element_available({"nvjpegdec", "nv3dsink"}),
        )
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("nv3dsink sync=false", command)
        self.assertNotIn("nveglglessink", command)

    def test_jetpack7_mjpeg_pipeline_includes_cropper(self):
        builder = GstPipelineBuilder(
            jetpack7.PROFILE,
            element_available=self.element_available(
                {"nvjpegdec", "nveglglessink"}
            ),
        )
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("videocrop name=cropper", command)

    def test_jetpack7_mjpeg_falls_back_to_jpegdec_when_nvjpegdec_unavailable(self):
        builder = GstPipelineBuilder(
            jetpack7.PROFILE,
            element_available=self.element_available(set()),
        )
        template = builder.build_template("uvcvideo", "/dev/video0", "MJPG")

        command = builder.build_preview_command(
            template,
            width="3840",
            height="2592",
            frame_rate="30",
            sync=False,
        )

        self.assertIn("jpegparse", command)
        self.assertIn("jpegdec", command)
        self.assertNotIn("nvjpegdec", command)
        self.assertIn("videocrop name=cropper", command)


if __name__ == "__main__":
    unittest.main()
