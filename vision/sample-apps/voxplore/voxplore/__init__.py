# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

try:
    import certifi

    ca_bundle = certifi.where()
    if os.path.exists(ca_bundle):
        os.environ.setdefault("SSL_CERT_FILE", ca_bundle)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_bundle)
except ImportError:
    pass

from . import genmedia  # noqa: F401
from .agent import (  # noqa: F401
    AVATARS,
    VOICES,
    app_name,
    default_avatar,
    default_voice,
    get_agent_setup_config,
    preset,
    proactive_default,
    root_agent,
)
from .models import ClientMessage, ServerMessage, SetupMessage  # noqa: F401
from .toolrunner import (  # noqa: F401
    add_upload,
    handle_scene_event,
    load_paper,
    remove_upload,
    run_function_call,
    set_mode,
)
from .tools import SessionState  # noqa: F401
