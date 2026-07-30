"""Shared pytest config — VCR cassettes for HTTP-backed scraper tests.

Cassettes live under ``test/cassettes/<module>/<test>.yaml`` and replay
real upstream responses captured once. Re-record with::

    pytest --vcr-record=all test/test_*_vcr.py

Live re-validation runs in the nightly CI workflow (no cassettes,
hits real endpoints) so cassette drift surfaces within 24 h.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["User-Agent", "Cookie", "Authorization"],
        "decode_compressed_response": True,
        "record_mode": "none",
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    return str(Path(request.module.__file__).parent / "cassettes" /
               Path(request.module.__file__).stem)
