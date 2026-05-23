import os
import unittest
from unittest.mock import patch

from camera_caps.gst import environment


class GstEnvironmentTest(unittest.TestCase):
    def test_detects_jetpack7_from_l4t_r38_release(self):
        self.assertEqual(
            environment.detect_jetpack_major(
                "# R38 (release), REVISION: 2.0, GCID: 123"
            ),
            7,
        )

    def test_detects_jetpack6_from_l4t_r36_release(self):
        self.assertEqual(
            environment.detect_jetpack_major(
                "# R36 (release), REVISION: 4.4, GCID: 123"
            ),
            6,
        )

    def test_default_profile_uses_jetpack7_on_l4t_r38(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "camera_caps.gst.environment.detect_jetpack_major",
                return_value=7,
            ):
                self.assertEqual(environment.default_profile().name, "jetpack7")

    def test_default_profile_can_be_overridden(self):
        with patch.dict(os.environ, {"CAMERA_CAPS_GST_PROFILE": "jetpack6"}):
            self.assertEqual(environment.default_profile().name, "jetpack6")


if __name__ == "__main__":
    unittest.main()
