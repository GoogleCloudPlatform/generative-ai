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

"""Evolution engines for Agent Platform version."""
from app.evolution.bigquery_dream_rsi import BigQueryDreamRSIEngine
from app.evolution.cloud_principle_store import CloudPrincipleStore, PrincipleRecord
from app.evolution.credit_attribution import CreditAttributionEngine, StepCreditAttribution
from app.evolution.topology_mutator import CloudTopologyMutator
from app.evolution.self_questioner import ShadowSandboxEnvironment

__all__ = [
    "BigQueryDreamRSIEngine",
    "CloudPrincipleStore",
    "PrincipleRecord",
    "CreditAttributionEngine",
    "StepCreditAttribution",
    "CloudTopologyMutator",
    "ShadowSandboxEnvironment",
]
