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


import asyncio
import datetime

from backend.app_logging import get_logger
from rich.console import Console
from tenacity import RetryCallState
from websockets import ConnectionClosedError, ConnectionClosedOK

logger = get_logger(__name__)

console = Console()


def format_dt(dt: datetime.datetime):
    return dt.strftime("%m-%d-%Y_%H:%M:%S")


def on_backoff(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    exc_info = f"{exc!r}" if exc else "No exception info"
    console.log(f"Security tool execution failed: {exc_info}. Retrying...")
    console.log(f"{retry_state.kwargs = }")


def retry_on_connection_error(retry_state: RetryCallState) -> bool:
    if retry_state.outcome is None:
        return False
    exc = retry_state.outcome.exception()
    if exc is None:
        return False

    if isinstance(exc, asyncio.TimeoutError):
        return True

    if isinstance(exc, (ConnectionClosedError, ConnectionClosedOK)):
        if (
            hasattr(exc, "code")
            and exc.code == 1011
            and hasattr(exc, "reason")
            and "Resource has been exhausted" in str(exc.reason)
        ):
            logger.warning(
                f"Gemini resource exhaustion error (code 1011) detected on attempt {retry_state.attempt_number}. "
                f"Not retrying. Exception: {exc!r}",
            )
            return False
        return True
    return False
