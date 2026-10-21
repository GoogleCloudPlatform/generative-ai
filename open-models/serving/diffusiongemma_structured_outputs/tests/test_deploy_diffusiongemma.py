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

"""Unit tests for deploy_diffusiongemma.py."""

import os
import unittest
from unittest import mock

import deploy_diffusiongemma


class TestDeployDiffusionGemma(unittest.TestCase):
    """Tests CLI argument builders and SDK calls in deploy_diffusiongemma."""

    def test_build_vllm_serve_args_includes_required_flags(self) -> None:
        # Verify _build_vllm_serve_args configures TRITON_ATTN and max-num-seqs.
        vllm_args = deploy_diffusiongemma._build_vllm_serve_args(
            max_num_seqs=16,
            gpu_util=0.92,
        )
        self.assertIn("--attention-backend=TRITON_ATTN", vllm_args)
        self.assertIn("--max-num-seqs=16", vllm_args)
        self.assertIn("--gpu-memory-utilization=0.92", vllm_args)
        self.assertIn("--enable-prefix-caching", vllm_args)

    @mock.patch.dict(os.environ, {"HF_TOKEN": "hf_test_secret"}, clear=False)
    def test_build_vllm_container_env_propagates_hf_token(self) -> None:
        # Verify _build_vllm_container_env sets VLLM_USE_V2_MODEL_RUNNER.
        env = deploy_diffusiongemma._build_vllm_container_env()
        self.assertEqual(env["VLLM_USE_V2_MODEL_RUNNER"], "1")
        self.assertEqual(env["HF_TOKEN"], "hf_test_secret")

    @mock.patch("deploy_diffusiongemma.aiplatform")
    def test_deploy_model_to_endpoint_reuses_existing_endpoint(
        self, mock_aiplatform: mock.MagicMock
    ) -> None:
        # Verify deploy_model_to_endpoint() reuses an active endpoint.
        fake_ep = mock.MagicMock()
        fake_ep.resource_name = "projects/1/locations/us-central1/endpoints/2"
        fake_ep.list_models.return_value = [mock.MagicMock()]
        mock_aiplatform.Endpoint.list.return_value = [fake_ep]

        result = deploy_diffusiongemma.deploy_model_to_endpoint(
            project="test-project", name="diffusiongemma-vllm"
        )
        self.assertIs(result, fake_ep)
        mock_aiplatform.Model.upload.assert_not_called()

    @mock.patch("deploy_diffusiongemma.aiplatform")
    def test_delete_endpoint_and_model_cleans_up_resources(
        self, mock_aiplatform: mock.MagicMock
    ) -> None:
        # Verify delete_endpoint_and_model() deletes both endpoint and model.
        fake_ep = mock.MagicMock()
        fake_ep.resource_name = "projects/1/locations/us-central1/endpoints/2"
        fake_model = mock.MagicMock()
        fake_model.resource_name = "projects/1/locations/us-central1/models/3"
        mock_aiplatform.Endpoint.list.return_value = [fake_ep]
        mock_aiplatform.Model.list.return_value = [fake_model]

        deploy_diffusiongemma.delete_endpoint_and_model(
            name="diffusiongemma-vllm"
        )
        fake_ep.delete.assert_called_once_with(force=True)
        fake_model.delete.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
