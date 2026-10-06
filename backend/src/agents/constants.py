"""Shared constants used across multiple agent nodes.

Centralizing public fallbacks and keyword lists here prevents agent nodes from
drifting into different user-facing behavior.
"""

PUBLIC_LLM_UNAVAILABLE_CODE = "SERVICE_TEMPORARILY_UNAVAILABLE"
PUBLIC_LLM_UNAVAILABLE_MESSAGE = (
    "ViVi đang tạm thời chưa thể xử lý yêu cầu này. Quý khách vui lòng thử lại sau."
)

# Keywords that bypass the LLM classifier and route directly to sensitive_policy_node
SOVEREIGNTY_KEYWORDS: list[str] = [
    "hoàng sa",
    "trường sa",
    "biển đông",
    "paracel",
    "spratly",
]

OUT_OF_SCOPE_KEYWORDS: list[str] = [
    "viết code",
    "lập trình",
    "python",
    "javascript",
    "code python",
    "viết script",
    "giải toán",
]

LOOKUP_KEYWORDS: list[str] = [
    "tra cứu lịch",
    "tra cuu lich",
    "xem lịch đã đặt",
    "xem lich da dat",
    "tìm lịch đã đặt",
    "tim lich da dat",
    "booking của tôi",
    "booking cua toi",
]

BOOKING_RESCHEDULE_KEYWORDS: list[str] = [
    "đổi lịch", "doi lich", "dời lịch", "doi lich", "sửa lịch", "sua lich",
    "đổi giờ", "doi gio", "dời giờ", "đổi ngày", "doi ngay", "chuyển lịch", "chuyen lich",
    "chuyển giờ", "chuyen gio", "chuyển ngày", "chuyen ngay", "hẹn trễ hơn", "hen tre hon",
]

BOOKING_CANCEL_KEYWORDS: list[str] = [
    "hủy lịch", "huỷ lịch", "huy lich", "hủy booking", "huỷ booking", "huy booking",
    "hủy luôn", "huỷ luôn", "huy luon",
]

# Natural-language requests are classified by the LLM first. These phrases are
# intentionally retained only for the technical-error fallback path.
BOOKING_MUTATION_KEYWORDS: list[str] = [
    "đặt lịch", "dat lich", "tìm showroom", "tim showroom", "tìm lịch", "tim lich",
    "giữ chỗ", "giu cho", "xác nhận đặt", "xac nhan dat", "tra cứu lịch", "tra cuu lich",
    "mã otp", "ma otp", "xác thực otp", "xac thuc otp",
    *BOOKING_RESCHEDULE_KEYWORDS,
    *BOOKING_CANCEL_KEYWORDS,
]

ADVISORY_KEYWORDS: list[str] = [
    "cần mang gì", "chuẩn bị", "nên thử", "nên kiểm tra", "nên hỏi", "lái thử",
    "pin", "sạc", "range", "quãng đường", "adas", "camera", "an toàn", "gia đình",
    "ghế trẻ em", "đỗ xe", "đậu xe", "hầm", "chi phí sử dụng", "xe điện",
]
