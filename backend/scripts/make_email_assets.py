"""Sinh ảnh dùng riêng cho email xác nhận lịch lái thử.

Chạy TAY, không chạy lúc gửi thư. Cần Pillow; tầng gửi thư KHÔNG cần Pillow.

    python backend/scripts/make_email_assets.py

Sinh hai nhóm:

  A. HAI DẢI LOGO, đều tràn hết bề ngang thư
     src/services/booking/assets/email-logo-band.png        (đầu thư)
     src/services/booking/assets/email-logo-band-small.png  (chân thư)

     Header nay CHỈ CÓ LOGO, đã bỏ khẩu hiệu. Dải rộng đúng 600px bằng bề ngang
     thư nên nó ăn khớp với mọi khối khác, không lộ mép.

     File logo gốc vinfast-logo.png là bản MÀU ĐEN (#231F20) dùng cho nền sáng,
     đặt lên nền đen là chìm nghỉm. Ở đây lấy khuôn từ kênh alpha của chính file
     gốc rồi tô TRẮNG: hình dạng không đổi, chỉ chuyển sang bản đơn sắc trắng cho
     nền tối. Không pha màu lạ vào logo.

     Nền tối nướng sẵn và dải rộng đúng 600px bằng bề ngang thư, xem lý do ở phần B.

  B. HAI Ô NỀN ĐẶC, dùng làm ẢNH NỀN cho thư
     src/services/booking/assets/email-bg-base.png   #121212, nền thư
     src/services/booking/assets/email-bg-card.png   #1E1E1E, nền card

     Đây là cách KHOÁ CỨNG màu thư, không cho ứng dụng mail đổi theo chế độ sáng
     tối của máy.

     Điểm mấu chốt: ỨNG DỤNG MAIL KHÔNG ĐẢO MÀU BÊN TRONG ẢNH, nó chỉ đảo màu
     khai báo bằng CSS. Nền khai bằng background-color thì bị lật; nền lát bằng
     một ô ảnh đặc thì không đụng vào được. Nhờ đó logo VinFast giữ nguyên bản
     gốc chữ trắng nền trong suốt mà vẫn luôn nằm trên nền tối.

     Ô nhỏ 24x24 rồi lát lặp (background-repeat), nhẹ vài trăm byte.

  B. ẢNH CHÌM SAU CARD, mỗi mẫu xe một file
     data/media/vehicle-media/<MÃ XE>/email-watermark.jpg

     Email không có opacity cho ảnh nền nên phải làm tối ảnh từ trước. Ba việc,
     bỏ việc nào cũng lộ ngay:

       1. CẮT NỬA PHẢI. Mép trái khung cắt xuyên qua thân xe, mép phải là khoảng
          trống sau mũi xe. Email neo ảnh vào left bottom nên chỗ cắt trùng đúng
          cạnh trái card, mắt đọc ra là xe đang tiến vào khung.
       2. NÂNG MỨC ĐEN lên đúng #1E1E1E, bằng nền card. Ảnh gốc nền #000000, không
          nâng thì ô ảnh hiện ra một hình chữ nhật lộ mép, cắt ngang dòng chữ trên.
       3. VUỐT MỜ mép phải và mép trên về màu nền card. KHÔNG vuốt mép trái vì đó
          là chỗ cắt cố ý, phải sắc để trùng cạnh khung.

     Chỉ nhận ảnh xe chụp trên NỀN ĐEN. Ảnh nền sáng hạ sáng xong thành một mảng
     xám có cạnh, xấu hơn là không có ảnh chìm. Mẫu nào không có thì bỏ trống,
     email tự bỏ qua ảnh chìm.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageEnhance
except ImportError:  # pragma: no cover - script chạy tay
    sys.exit("Cần Pillow: pip install Pillow")

_REPO = Path(__file__).resolve().parents[2]
ASSETS = _REPO / "backend" / "src" / "services" / "booking" / "assets"
MEDIA_ROOT = _REPO / "backend" / "data" / "media" / "vehicle-media"
# publish_site_media.py copy từ cây frontend đè sang backend. Ghi ảnh vào cả hai
# cây thì chạy lại lệnh publish không làm mất ảnh chìm, và đẩy R2 từ cây nào cũng đủ.
FRONTEND_MEDIA_ROOT = _REPO / "frontend" / "src" / "media" / "local" / "vehicle-media"

BASE = (18, 18, 18)          # #121212 Rich Black
CARD_BG = (30, 30, 30)       # #1E1E1E Charcoal Dark

WATERMARK_NAME = "email-watermark.jpg"
WATERMARK_WIDTH = 760
WATERMARK_BRIGHTNESS = 0.21

# Ảnh chìm cho thư OTP: xe Lạc Hồng, không gắn với mẫu xe nào cả.
LAC_HONG_SOURCE = _REPO / "frontend" / "src" / "media" / "local" / "showcase" / "lac-hong-900lx" / "spin-2.webp"
LAC_HONG_TARGET = _REPO / "backend" / "data" / "media" / "email" / "lac-hong-watermark.jpg"

SOURCES: dict[str, str] = {
    "VF3": "VF3/2.png",
    "VF5": "VF5/trắng.webp",
    "VF7": "VF7/product-CE18.webp",
    "VF8": "VF8/vf8eco.webp",
    "VF9": "VF9/CE18.webp",
    # VF6 không có ảnh nào chụp trên nền đen nên bỏ trống.
}


def _tile(color: tuple[int, int, int]) -> Image.Image:
    """Ô màu đặc 24x24 để lát nền. Nhỏ nhất có thể mà vẫn không lộ mối lát."""
    return Image.new("RGB", (24, 24), color)


def _logo_band(mark_width: int, band_height: int, scale: int = 2) -> Image.Image:
    """Dải logo tràn ngang: chữ VinFast MÀU TRẮNG trên nền tối của thư.

    Hai việc file gốc không làm được, nên phải dựng lại:

    1. FILE GỐC LÀ LOGO MÀU ĐEN (#231F20) dùng cho nền sáng. Đặt nguyên lên nền
       đen thì chìm nghỉm. Ở đây lấy kênh alpha của file gốc làm khuôn rồi tô
       TRẮNG. Hình dạng logo không đổi một pixel nào; chỉ đổi sang bản đơn sắc
       trắng, đúng bản mà mọi bộ nhận diện đều có cho nền tối.

    2. NỀN TỐI NƯỚNG SẴN, và dải rộng đúng 600px bằng bề ngang thư. Ứng dụng mail
       trên điện thoại tự đảo màu nền theo chế độ máy; nền khai bằng CSS thì bị
       lật, còn ảnh thì không. Dải rộng hết khổ nên khi thư hiện đúng màu nó tan
       vào nền, còn khi bị lật màu nó đọc ra là một dải header cố ý chứ không
       phải một ô chữ nhật lạc lõng.

    Màu chữ logo vẫn là màu gốc của bộ nhận diện (trắng), KHÔNG pha màu lạ vào.
    """
    mask = Image.open(ASSETS / "vinfast-logo.png").convert("RGBA").getchannel("A")
    width = int(mark_width * scale)
    mask = mask.resize((width, int(width * mask.height / mask.width)), Image.LANCZOS)

    band = Image.new("RGB", (600 * scale, band_height * scale), BASE)
    band.paste(
        Image.new("RGB", mask.size, (255, 255, 255)),
        ((band.width - mask.width) // 2, (band.height - mask.height) // 2),
        mask,
    )
    return band


def build_watermark(source: Path, target: Path) -> None:
    im = Image.open(source).convert("RGB")
    w, h = im.size
    im = im.crop((int(w * 0.46), int(h * 0.20), w, int(h * 0.90)))
    im = ImageEnhance.Brightness(im).enhance(WATERMARK_BRIGHTNESS)
    im = ImageChops.add(im, Image.new("RGB", im.size, CARD_BG))
    im = im.resize((WATERMARK_WIDTH, int(WATERMARK_WIDTH * im.height / im.width)), Image.LANCZOS)

    width, height = im.size
    mask = Image.new("L", (width, height), 255)
    pixels = mask.load()
    fade_x, fade_y = int(width * 0.22), int(height * 0.28)
    for x in range(width):
        ax = min(1.0, (width - 1 - x) / fade_x)
        for y in range(height):
            pixels[x, y] = int(255 * ax * min(1.0, y / fade_y))
    im = Image.composite(im, Image.new("RGB", (width, height), CARD_BG), mask)

    target.parent.mkdir(parents=True, exist_ok=True)
    im.save(target, quality=88, optimize=True, progressive=True)


def main() -> int:
    print("Logo:")
    for name, mark_width, band_height, note in (
        ("email-logo-band.png", 240, 120, "đầu thư"),
        ("email-logo-band-small.png", 150, 82, "chân thư"),
    ):
        target = ASSETS / name
        _logo_band(mark_width, band_height).save(target, optimize=True)
        print(f"  {target.relative_to(_REPO)}  {target.stat().st_size // 1024} KB  ({note})")
    (ASSETS / "email-logo-tile.png").unlink(missing_ok=True)

    print("Ô nền:")
    for name, color in (("email-bg-base.png", BASE), ("email-bg-card.png", CARD_BG)):
        target = ASSETS / name
        _tile(color).save(target, optimize=True)
        print(f"  {target.relative_to(_REPO)}  {target.stat().st_size} byte")
    for stale in ("email-logo-gold.png", "email-logo-dark.png"):
        (ASSETS / stale).unlink(missing_ok=True)

    print("Ảnh chìm thư OTP:")
    if LAC_HONG_SOURCE.is_file():
        build_watermark(LAC_HONG_SOURCE, LAC_HONG_TARGET)
        print(f"  {LAC_HONG_TARGET.relative_to(_REPO)}  {LAC_HONG_TARGET.stat().st_size // 1024} KB")
        mirror = _REPO / "frontend" / "src" / "media" / "local" / "email" / "lac-hong-watermark.jpg"
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_bytes(LAC_HONG_TARGET.read_bytes())
    else:
        print(f"  BỎ QUA: thiếu ảnh nguồn {LAC_HONG_SOURCE}")

    print("Ảnh chìm theo mẫu xe:")
    missing = []
    for code, relative in SOURCES.items():
        source = MEDIA_ROOT / relative
        if not source.is_file():
            missing.append(f"{code}: thiếu ảnh nguồn {relative}")
            continue
        target = MEDIA_ROOT / code / WATERMARK_NAME
        build_watermark(source, target)
        print(f"  {code}  {target.relative_to(_REPO)}  {target.stat().st_size // 1024} KB")
        mirror = FRONTEND_MEDIA_ROOT / code / WATERMARK_NAME
        if mirror.parent.is_dir():
            mirror.write_bytes(target.read_bytes())
    for line in missing:
        print(f"  BỎ QUA {line}")
    print("Nhớ đẩy ảnh chìm lên CDN, nếu không email trên môi trường thật không thấy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
