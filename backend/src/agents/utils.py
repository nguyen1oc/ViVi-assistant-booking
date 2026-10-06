from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.md"
MAX_LLM_HISTORY_MESSAGES = 24

def window_messages(messages: list[AnyMessage], limit: int = MAX_LLM_HISTORY_MESSAGES) -> list[AnyMessage]:
    """Keep recent conversation turns without separating tool calls from results."""
    if len(messages) <= limit:
        return messages

    groups: list[list[AnyMessage]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        group = [message]
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_call_ids = {str(call.get("id", "")) for call in message.tool_calls}
            index += 1
            while index < len(messages):
                candidate = messages[index]
                if not isinstance(candidate, ToolMessage) or candidate.tool_call_id not in tool_call_ids:
                    break
                group.append(candidate)
                index += 1
            groups.append(group)
            continue
        groups.append(group)
        index += 1

    recent: list[AnyMessage] = []
    for group in reversed(groups):
        if recent and len(group) + len(recent) > limit:
            break
        recent = group + recent
    return recent

def get_system_prompt() -> str:
    try:
        with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
            content = f.read()
            weekdays_vi = {
                0: "Thứ 2",
                1: "Thứ 3",
                2: "Thứ 4",
                3: "Thứ 5",
                4: "Thứ 6",
                5: "Thứ 7",
                6: "Chủ nhật"
            }
            now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
            weekday_str = weekdays_vi[now.weekday()]
            date_str = now.strftime("%Y-%m-%d %H:%M:%S")
            time_context = f"\n\n--- CURRENT TIME CONTEXT ---\nToday is: {weekday_str}, {date_str} (Vietnam Local Time)"
            return content + time_context
    except Exception:
        return "You are Vini, the VinFast Test Drive Virtual Assistant."
