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

"""scripts/provision_docs.py: which local files get uploaded (no network)."""

import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "provision_docs", os.path.join(ROOT, "scripts", "provision_docs.py")
)
provision_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(provision_docs)


def test_default_include_uploads_pdfs_only():
    pats = [provision_docs.DEFAULT_INCLUDE]
    assert provision_docs.matches_include("acme-cloud-pricing.pdf", pats)
    assert provision_docs.matches_include("GUIDE.PDF", pats)
    assert not provision_docs.matches_include("acme-cloud-pricing.html", pats)
    assert not provision_docs.matches_include(".hidden.pdf", pats)


def test_custom_include_patterns():
    pats = ["*.pdf", " *.docx"]
    assert provision_docs.matches_include("handbook.docx", pats)
    assert provision_docs.matches_include("plans.pdf", pats)
    assert not provision_docs.matches_include("notes.txt", pats)


def test_upload_local_dir_skips_non_matching_files(tmp_path, monkeypatch):
    for name in ("a.pdf", "a.html", "b.pdf", ".DS_Store"):
        (tmp_path / name).write_text("x")
    uploaded = []

    class Blob:
        def __init__(self, name):
            self.name = name

        def upload_from_filename(self, path):
            uploaded.append(self.name)

    class Bucket:
        def blob(self, name):
            return Blob(name)

    class Client:
        def bucket(self, name):
            return Bucket()

    fake_storage = types.SimpleNamespace(Client=Client)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", fake_storage)
    import google.cloud

    monkeypatch.setattr(google.cloud, "storage", fake_storage, raising=False)

    provision_docs.upload_local_dir(str(tmp_path), "gs://bucket/acme-cloud/")
    assert sorted(uploaded) == ["acme-cloud/a.pdf", "acme-cloud/b.pdf"]
