from langchain_core.messages import AIMessage

from src.agents.state import AgentState


async def sensitive_policy_node(state: AgentState) -> dict:
    """Xử lý các chủ đề nhạy cảm hoặc tác vụ nằm ngoài phạm vi nghiệp vụ lái thử xe.

    Lưu ý: Node này chỉ cần đọc sub_intent từ metadata (đã được classifier_node set).
    Không cần check lại keyword vì classifier_node đã xử lý việc đó rồi.
    """
    existing_policy_response = state.get("policy_response")
    if existing_policy_response:
        return {
            "response": existing_policy_response,
            "policy_response": existing_policy_response,
            "messages": [AIMessage(content=existing_policy_response)],
        }

    sub_intent = (state.get("metadata") or {}).get("sub_intent", "")

    if sub_intent == "sovereignty":
        response = "Quần đảo Hoàng Sa và quần đảo Trường Sa hoàn toàn thuộc chủ quyền của Việt Nam."
    elif sub_intent == "party_history":
        response = (
            "Đảng Cộng sản Việt Nam được thành lập ngày 3/2/1930. "
            "ViVi có thể tiếp tục hỗ trợ Quý khách về xe VinFast và lịch lái thử."
        )
    elif sub_intent == "ho_chi_minh_history":
        response = (
            "Chủ tịch Hồ Chí Minh (1890–1969) là lãnh tụ của cách mạng Việt Nam "
            "và là người sáng lập nước Việt Nam Dân chủ Cộng hòa."
        )
    elif sub_intent == "out_of_scope_code":
        response = (
            "ViVi là Trợ lý ảo hỗ trợ lái thử xe VinFast. "
            "ViVi không hỗ trợ viết mã lập trình hoặc các tác vụ phần mềm khác. "
            "ViVi có thể giúp gì cho bạn về đặt lịch lái thử xe điện VinFast không?"
        )
    elif sub_intent == "out_of_scope_math":
        response = (
            "ViVi là Trợ lý ảo hỗ trợ lái thử xe VinFast. "
            "ViVi không hỗ trợ giải các bài toán học. "
            "ViVi có thể giúp gì cho bạn về đặt lịch lái thử xe điện VinFast không?"
        )
    elif sub_intent == "post_booking_required":
        response = (
            "ViVi hiện chỉ hỗ trợ đặt lịch lái thử xe điện VinFast. "
            "Tính năng tư vấn thông tin xe và hướng dẫn sau khi đặt lịch chỉ khả dụng "
            "khi bạn đã có lịch lái thử được xác nhận."
        )
    elif sub_intent == "out_of_scope":
        response = (
            "Nội dung này nằm ngoài phạm vi hỗ trợ hiện tại của ViVi. "
            "ViVi có thể giúp Quý khách tìm hiểu xe VinFast, tìm showroom, kiểm tra lịch trống "
            "và đặt hoặc quản lý lịch lái thử."
        )
    else:
        # Default fallback for foreign locations or general out-of-scope queries
        response = (
            "Hiện tại ViVi hỗ trợ đặt lịch lái thử xe điện VinFast trên toàn lãnh thổ Việt Nam. "
            "Quý khách có thể chọn một tỉnh thành/địa điểm tại Việt Nam hoặc mẫu xe để ViVi hỗ trợ nhé!"
        )

    return {
        "response": response,
        "policy_response": response,
        "messages": [AIMessage(content=response)],
    }
