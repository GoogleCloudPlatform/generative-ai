#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for config.py."""

import os
import unittest
from unittest import mock

import config


class TestConfig(unittest.TestCase):
    """Tests environment variable and project resolution in config.py."""

    @mock.patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "[your-project-id]"}, clear=False
    )
    @mock.patch("config.google.auth.default")
    def test_resolve_default_project_ignores_placeholder(
        self, mock_auth_default: mock.MagicMock
    ) -> None:
        # Verify placeholder project IDs are stripped in favor of ADC.
        mock_auth_default.return_value = (None, "adc-resolved-project")
        proj = config.resolve_default_project()
        self.assertEqual(proj, "adc-resolved-project")
        self.assertNotIn("GOOGLE_CLOUD_PROJECT", os.environ)

    @mock.patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "explicit-project"}, clear=False
    )
    def test_resolve_default_project_uses_env_var(self) -> None:
        # Verify explicit GOOGLE_CLOUD_PROJECT environment variable is used.
        self.assertEqual(config.resolve_default_project(), "explicit-project")


if __name__ == "__main__":
    unittest.main()
