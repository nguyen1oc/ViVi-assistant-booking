import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

# Setup mock objects identical to conftest.py
mock_instance = MagicMock()
mock_response = AIMessage(content="Mocked LLM response (This is a mock answer for testing)")
mock_instance.ainvoke = AsyncMock(return_value=mock_response)
mock_instance.bind_tools = MagicMock(return_value=mock_instance)

mock_structured = MagicMock()


async def mock_classify(prompt, **kwargs):
    from src.agents.nodes.classifier_node import RouteSchema

    prompt_lower = prompt.lower()
    query_part = prompt_lower.split("user query:")[-1] if "user query:" in prompt_lower else prompt_lower
    query_clean = "".join(c if c.isalnum() or c.isspace() else " " for c in query_part)
    words = query_clean.split()
    if any(kw in words for kw in ["chào", "hello", "hi"]):
        return RouteSchema(intent="domain", sub_intent="vehicle_info", has_schedule_preference=False)
    elif any(kw in words or kw in query_part for kw in ["vf8", "sạc", "km", "thông số", "giá"]):
        return RouteSchema(intent="domain", sub_intent="vehicle_info", has_schedule_preference=False)
    return RouteSchema(intent="domain", sub_intent="booking", has_schedule_preference=False)


mock_structured.ainvoke = AsyncMock(side_effect=mock_classify)
mock_instance.with_structured_output = MagicMock(return_value=mock_structured)


async def run_trial():
    # Patch ChatOpenAI globally before loading the agent graph
    with patch("src.services.llm.ChatOpenAI", return_value=mock_instance):
        from src.agents.graph import agent

        questions = [
            "Xin chào bạn nhé!",
            "Dung lượng pin xe VF8 là bao nhiêu?",
            "Tôi muốn đặt lịch lái thử xe VF3 tại Hà Nội",
        ]

        print("\n" + "=" * 60)
        print("🚀 CHẠY THỬ NGHIỆM ĐỊNH TUYẾN ĐỒ THỊ LANGGRAPH (MOCK)")
        print("=" * 60 + "\n")

        for idx, q in enumerate(questions, 1):
            print(f'Case #{idx}: Query = "{q}"')
            print("-" * 50)
            result = await agent.ainvoke({"query": q})
            print(f"  ➜ Phân loại Intent: {result.get('intent')}")
            print(f"  ➜ Skill kích hoạt : {result.get('active_skill')}")
            print(f"  ➜ Phản hồi Mock   : {result.get('response')}")
            print("-" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_trial())
