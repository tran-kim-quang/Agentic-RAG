import sys
sys.path.insert(0, "/home/meocon/work/sideprj")
import pytest
from retrieval_service.client import RetrievalClient


@pytest.mark.asyncio
async def test_retrieval_client_embed():
    client = RetrievalClient()
    vec = await client._embed("căn hộ 2 phòng ngủ")
    assert isinstance(vec, list)
    assert len(vec) == 768
