import asyncio
import os
import sys

import pytest

# Ensure backend src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.tools.search_test_drive_options.tool import search_test_drive_options
from src.services.llm import get_llm


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM_TESTS") != "1",
    reason="Real LLM smoke test is opt-in; set RUN_REAL_LLM_TESTS=1 to run it.",
)
@pytest.mark.asyncio
async def test_llm():
    llm = get_llm()
    if llm is None:
        pytest.skip("No LLM provider key is configured.")

    llm_with_tools = llm.bind_tools([search_test_drive_options])
    response = await llm_with_tools.ainvoke(
        "Tôi muốn lái thử xe VF3 ở Hà Nội. Hãy gọi tool để tìm showroom."
    )

    assert hasattr(response, "content")
    assert hasattr(response, "tool_calls")


if __name__ == "__main__":
    asyncio.run(test_llm())
