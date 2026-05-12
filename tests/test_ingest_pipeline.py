import sys
sys.path.insert(0, "/home/meocon/work/sideprj")
import pytest
from ingest_service.pipeline import chunk_markdown


def test_chunk_markdown_splits_correctly():
    text = "Câu một. Câu hai. Câu ba. Câu bốn."
    chunks = chunk_markdown(text, chunk_size=20, overlap=5)
    assert len(chunks) >= 2
    assert all(len(c) <= 50 for c in chunks)  # generous upper bound
