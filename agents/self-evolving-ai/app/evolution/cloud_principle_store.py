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

"""Google Cloud Agent Platform-backed Semantic Principle Vector Store with KMS Signing."""
import hashlib
import re
import time
from typing import List, Dict, Optional, Tuple
import numpy as np
from pydantic import BaseModel

from app.config import PROJECT_ID, LOCATION, EMBEDDING_MODEL, VERTEX_AI_AVAILABLE
from app.governance.kms_signer import CloudKmsSigner, KmsSignatureEnvelope

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class PrincipleRecord(BaseModel):
    """A distilled operational principle with its embedding and Cloud KMS signature."""

    principle_id: str
    trigger_pattern: str
    contraindicated_actions: List[str]
    recommended_actions: List[str]
    confidence_score: float
    source_incident_id: str
    created_at: str
    embedding: Optional[List[float]] = None
    kms_signature: Optional[KmsSignatureEnvelope] = None


class CloudPrincipleStore:
    """Semantic vector store built on Agent Platform text-embedding-004 and signed by Cloud KMS."""

    def __init__(
        self,
        project_id: str = PROJECT_ID,
        location: str = LOCATION,
        model_name: str = EMBEDDING_MODEL,
    ):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.kms_signer = CloudKmsSigner(project_id=project_id)
        self.principles: Dict[str, PrincipleRecord] = {}

        self._genai_client = None
        if GENAI_AVAILABLE and VERTEX_AI_AVAILABLE:
            try:
                self._genai_client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                self._genai_client = None

        self._seed_baseline_principles()
        # Snapshot the Day-0 guardrails so a reset can restore them exactly (without re-embedding /
        # re-signing). A learned principle with the same trigger text shares the seed's ID and would
        # otherwise silently replace it.
        self._baseline_records: Dict[str, PrincipleRecord] = dict(self.principles)

    def reset_to_baseline(self) -> int:
        """Forget principles learned since Day-0 and restore the seeded guardrails. Returns count removed."""
        learned = sum(1 for pid, rec in self.principles.items() if self._baseline_records.get(pid) is not rec)
        self.principles.clear()
        self.principles.update(self._baseline_records)
        return learned

    def discard(self, principle_id: str) -> None:
        """Remove a learned principle (restoring the seeded record if it had replaced one)."""
        if principle_id in self._baseline_records:
            self.principles[principle_id] = self._baseline_records[principle_id]
        else:
            self.principles.pop(principle_id, None)

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate 768-dim semantic vector embedding using Agent Platform text-embedding-004."""
        if self._genai_client:
            try:
                resp = self._genai_client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                )
                if hasattr(resp, "embeddings") and resp.embeddings:
                    return list(resp.embeddings[0].values)
            except Exception:  # pylint: disable=broad-exception-caught
                self._genai_client = None

        # Deterministic offline fallback (dimension 768): feature-hashed bag of words, L2-normalized.
        # Texts sharing vocabulary get high cosine similarity, so retrieval stays meaningful offline;
        # md5 (not Python's per-process salted hash()) keeps vectors stable across runs.
        vec = np.zeros(768, dtype=float)
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            vec[int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % 768] += 1.0
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist() if norm > 0 else vec.tolist()

    def add_principle(
        self,
        trigger_pattern: str,
        contraindicated: List[str],
        recommended: List[str],
        confidence: float,
        incident_id: str = "INC-PLATFORM-001",
    ) -> PrincipleRecord:
        """Store an operational principle signed with Cloud KMS."""
        pid = f"PRIN-CLOUD-{abs(hash(trigger_pattern)) % 1000000:06X}"
        emb = self._generate_embedding(trigger_pattern)

        # Cryptographically sign the distilled invariant
        payload = f"{pid}:{trigger_pattern}:{contraindicated}:{recommended}"
        sig_envelope = self.kms_signer.sign_artifact(payload, artifact_type="PRINCIPLE")

        record = PrincipleRecord(
            principle_id=pid,
            trigger_pattern=trigger_pattern,
            contraindicated_actions=contraindicated,
            recommended_actions=recommended,
            confidence_score=confidence,
            source_incident_id=incident_id,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            embedding=emb,
            kms_signature=sig_envelope,
        )
        self.principles[pid] = record
        return record

    def query_similar_principles(self, incident_description: str, top_k: int = 3) -> List[Tuple[PrincipleRecord, float]]:
        """Query principles using cosine similarity over Agent Platform vector space."""
        query_emb = np.array(self._generate_embedding(incident_description))
        scored = []

        for p in self.principles.values():
            if p.embedding:
                p_emb = np.array(p.embedding)
                denom = np.linalg.norm(query_emb) * np.linalg.norm(p_emb)
                sim = float(np.dot(query_emb, p_emb) / denom) if denom > 0 else 0.0
                scored.append((p, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _seed_baseline_principles(self) -> None:
        """Seed Self-Navigating historical guardrails into Agent Platform vector memory."""
        self.add_principle(
            trigger_pattern="Cache eviction stampede causing database connection pool saturation under high ingress",
            contraindicated=["restart_database", "reboot_database", "flush_db_connections", "increase_db_pool_timeout"],
            recommended=["deploy_token_bucket_rate_limiter", "throttle_ingress_boundary", "shed_non_critical_load"],
            confidence=0.96,
            incident_id="INC-HIST-CLOUD-01",
        )
        self.add_principle(
            trigger_pattern="Transient network partition between microservices causing retry storm",
            contraindicated=["immediate_retries_without_backoff", "drop_ingress_circuit_breakers"],
            recommended=["exponential_backoff_with_jitter", "activate_adaptive_concurrency_limits"],
            confidence=0.91,
            incident_id="INC-HIST-CLOUD-02",
        )
