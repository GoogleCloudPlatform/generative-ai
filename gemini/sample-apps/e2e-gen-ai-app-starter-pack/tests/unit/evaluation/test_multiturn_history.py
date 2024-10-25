# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=R0801

from app.eval.utils import generate_multiturn_history
import pandas as pd
import pytest
import yaml


@pytest.mark.asyncio
async def test_multiturn_history() -> None:
    """Tests multi turn evaluation including tool calls in the conversation."""
    with open("tests/unit/evaluation/ml_ops_chat.yaml") as file:
        y = yaml.safe_load(file)
        df = pd.DataFrame(y)
        df = generate_multiturn_history(df)

    assert len(df) == 2
    assert df["conversation_history"][0] == []
    assert df["human_message"][0]["content"][0]["text"] == "Explain what's MLOps"
    assert len(df["conversation_history"][1]) == 4
    assert (
        df["human_message"][1]["content"][0]["text"] == "How can I evaluate my models?"
    )
