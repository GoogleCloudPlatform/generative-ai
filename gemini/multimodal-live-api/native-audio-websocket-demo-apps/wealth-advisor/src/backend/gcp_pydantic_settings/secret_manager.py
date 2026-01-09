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


from collections.abc import Iterator, Mapping
from functools import cached_property
from typing import TYPE_CHECKING, Optional

import google.auth

from google.cloud.secretmanager import SecretManagerServiceClient
from pydantic_settings import BaseSettings
from pydantic_settings.sources import EnvSettingsSource

if TYPE_CHECKING:
    from google.auth.credentials import Credentials  # pragma: no cover


class GoogleSecretManagerMapping(Mapping[str, Optional[str]]):
    _loaded_secrets: dict[str, str | None]
    _secret_client: SecretManagerServiceClient

    def __init__(self, secret_client: SecretManagerServiceClient, project_id: str) -> None:
        self._loaded_secrets = {}
        self._secret_client = secret_client
        self._project_id = project_id

    @property
    def _gcp_project_path(self) -> str:
        return self._secret_client.common_project_path(self._project_id)

    @cached_property
    def _secret_names(self) -> list[str]:
        try:
            return [
                self._secret_client.parse_secret_path(secret.name).get("secret", "")
                for secret in self._secret_client.list_secrets(parent=self._gcp_project_path)
            ]
        except Exception:
            # If we can't list secrets (permissions, wrong project, etc.), just return empty.
            # This prevents the application from crashing on startup if Secret Manager is inaccessible.
            return []

    def _secret_version_path(self, key: str, version: str = "latest"):
        return self._secret_client.secret_version_path(self._project_id, key, version)

    def __getitem__(self, key: str) -> str | None:
        if key not in self._loaded_secrets:
            # If we know the key isn't available in secret manager, raise a key error
            if key not in self._secret_names:
                raise KeyError(key)

            try:
                self._loaded_secrets[key] = self._secret_client.access_secret_version(
                    name=self._secret_version_path(key)
                ).payload.data.decode("UTF-8")
            except Exception:
                raise KeyError(key)

        return self._loaded_secrets[key]

    def __len__(self) -> int:
        return len(self._secret_names)

    def __iter__(self) -> Iterator[str]:
        return iter(self._secret_names)


class GoogleSecretManagerSettingsSource(EnvSettingsSource):
    _credentials: "Credentials"
    _secret_client: SecretManagerServiceClient
    _project_id: str

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        credentials: "Credentials | None" = None,
        project_id: str | None = None,
        env_prefix: str | None = None,
        env_parse_none_str: str | None = None,
        env_parse_enums: bool | None = None,
        secret_client: SecretManagerServiceClient | None = None,
    ) -> None:
        # If credentials or project_id are not passed, then
        # try to get them from the default
        if not credentials or not project_id:
            _creds, _project_id = google.auth.default()

        # Set the credentials and/or project id if they weren't specified
        if not credentials:
            credentials = _creds  # type: ignore

        if not project_id:
            project_id = _project_id  # type: ignore

        self._credentials = credentials  # type: ignore
        self._project_id = project_id  # type: ignore

        if secret_client:
            self._secret_client = secret_client
        else:
            self._secret_client = SecretManagerServiceClient(credentials=self._credentials)

        super().__init__(
            settings_cls,
            case_sensitive=True,
            env_prefix=env_prefix,
            env_ignore_empty=False,
            env_parse_none_str=env_parse_none_str,
            env_parse_enums=env_parse_enums,
        )

    def _load_env_vars(self) -> Mapping[str, Optional[str]]:
        return GoogleSecretManagerMapping(self._secret_client, project_id=self._project_id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(project_id={self._project_id!r}, env_nested_delimiter={self.env_nested_delimiter!r})"
        # return f"{self.__class__.__name__}(project_id={self._project_id!r})"
