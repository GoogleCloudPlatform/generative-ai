import os
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def mock_screen_dimensions():
    with mock.patch.dict(
        os.environ, {"HEIGHT": "768", "WIDTH": "1024", "DISPLAY_NUM": "1"}
    ):
        yield
