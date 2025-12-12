# Copyright 2025 Google LLC
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

# Copyright 2025 Google LLC
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


from datetime import datetime, timedelta

# from .app_settings import SERVICE_ACCOUNT_PATH, APISettings, ApplicationSettings
from .settings import APISettings, ApplicationSettings

_app_settings = None
_last_update = None


def get_application_settings() -> ApplicationSettings:
    """Gets the application settings with automatic refresh mechanism.

    This function implements a singleton pattern with a time-based refresh mechanism.
    It returns a cached instance of ApplicationSettings if one exists and was created
    within the last 15 minutes. Otherwise, it creates a new instance by fetching
    fresh values from Google Secret Manager.

    Returns:
        ApplicationSettings: The application settings instance, either cached or freshly created.

    Note:
        The function maintains a global instance and timestamp to implement the caching
        mechanism. Settings are automatically refreshed if they are older than 15 minutes
        or if no cached instance exists.
    """
    global _app_settings, _last_update

    if _app_settings and _last_update and (datetime.now() - _last_update) <= timedelta(minutes=15):
        return _app_settings
    else:
        _app_settings = ApplicationSettings()  # type: ignore
        _last_update = datetime.now()
        return _app_settings


__all__ = ["ApplicationSettings", "APISettings", "get_application_settings"]
