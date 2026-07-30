from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_examples import generate_all


@pytest.fixture(scope="session")
def example_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("proofmill-pdfs")
    generate_all(destination)
    return destination
