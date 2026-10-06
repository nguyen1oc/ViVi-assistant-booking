"""Read-only website catalogue and editorial content.

This module is deliberately independent from booking and Agent orchestration so
the public website contract can evolve without registering or invoking tools.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.config import get_settings
from src.models.site import CatalogSnapshot

REVISION = "2026-08-04"


def _media(url: str, alt: str, **extra: Any) -> dict[str, Any]:
    return {"url": url, "alt": alt, **extra}


_VEHICLES: list[dict[str, Any]] = [
    {"id": "vf3", "name": "VF 3", "category": "personal", "bodyType": "Mini eSUV", "seats": 4, "displayPrice": "Giá niêm yết · 299.000.000 VNĐ", "tagline": "Chất riêng trên mọi nẻo đường.", "specs": [("Quãng đường NEDC", "215 km"), ("Công suất tối đa", "32 kW")]},
    {"id": "vf5", "name": "VF 5", "category": "personal", "bodyType": "SUV hạng A", "seats": 5, "displayPrice": "Giá niêm yết · 529.000.000 VNĐ", "tagline": "Sống động từng nhịp phố.", "specs": [("Quãng đường NEDC", "326 km"), ("Công suất tối đa", "100 kW")]},
    {"id": "vf6", "name": "VF 6", "category": "personal", "bodyType": "SUV hạng B", "seats": 5, "displayPrice": "Giá niêm yết · 689.000.000 VNĐ", "tagline": "Mạnh mẽ và tinh tế.", "specs": [("Quãng đường NEDC", "460 km"), ("Công suất tối đa", "150 kW")]},
    {"id": "vf7", "name": "VF 7", "category": "personal", "bodyType": "SUV hạng C", "seats": 5, "displayPrice": "Giá niêm yết · 799.000.000 VNĐ", "tagline": "Dẫn lối đam mê.", "specs": [("Quãng đường WLTP", "431 km"), ("Công suất bản Plus", "260 kW")]},
    {"id": "vf-mpv-7", "name": "VF MPV 7", "category": "personal", "bodyType": "MPV điện gia đình", "seats": 7, "displayPrice": "Giá niêm yết · 750.000.000 VNĐ", "tagline": "Rộng rãi cho cả gia đình.", "specs": [("Quãng đường NEDC", "450 km"), ("Công suất tối đa", "150 kW")]},
    {"id": "vf8", "name": "VF 8", "category": "personal", "bodyType": "SUV hạng D", "seats": 5, "displayPrice": "Giá niêm yết · 1.020.000.000 VNĐ", "tagline": "Cùng bạn bứt phá mọi giới hạn.", "specs": [("Quãng đường bản Eco", "420 km"), ("Công suất bản Plus", "300 kW")]},
    {"id": "vf8-the-he-moi", "name": "VF 8 Thế hệ mới", "category": "personal", "bodyType": "SUV hạng D", "seats": 5, "displayPrice": "Liên hệ", "tagline": "Một nhịp nhìn mới.", "specs": [("Dẫn động", "AWD"), ("Nhiên liệu", "Điện")]},
    {"id": "vf9", "name": "VF 9", "category": "personal", "bodyType": "SUV hạng E", "seats": 7, "displayPrice": "Giá niêm yết · 1.499.000.000 VNĐ", "tagline": "Uy lực và tiện nghi.", "specs": [("Sức chứa", "7 chỗ"), ("Dẫn động", "AWD")]},
    {"id": "herio-green", "name": "Herio Green", "category": "fleet", "bodyType": "eSUV dịch vụ", "seats": 5, "displayPrice": "Chính sách dành cho kinh doanh", "tagline": "Bền bỉ cho nhịp vận hành.", "specs": [("Quãng đường NEDC", "326 km"), ("Công suất", "100 kW")]},
    {"id": "minio-green", "name": "Minio Green", "category": "fleet", "bodyType": "Mini car dịch vụ", "seats": 4, "displayPrice": "Chính sách dành cho kinh doanh", "tagline": "Nhỏ gọn, xoay trở tức thì.", "specs": [("Quãng đường NEDC", "210 km"), ("Công suất", "30 kW")]},
    {"id": "nerio-green", "name": "Nerio Green", "category": "fleet", "bodyType": "eSUV dịch vụ", "seats": 5, "displayPrice": "Chính sách dành cho kinh doanh", "tagline": "Không gian rộng, vận hành gọn.", "specs": [("Quãng đường tham chiếu", "318 km"), ("Công suất", "110 kW")]},
    {"id": "limo-green", "name": "Limo Green", "category": "fleet", "bodyType": "MPV điện dịch vụ", "seats": 7, "displayPrice": "Chính sách dành cho kinh doanh", "tagline": "Rộng rãi cho mọi hành trình.", "specs": [("Quãng đường NEDC", "450 km"), ("Công suất", "150 kW")]},
    {"id": "ec-van", "name": "EC Van", "category": "fleet", "bodyType": "Van điện chở hàng", "seats": 2, "displayPrice": "Chính sách dành cho kinh doanh", "tagline": "Giao hàng bằng năng lượng sạch.", "specs": [("Quãng đường NEDC", "175 km"), ("Khoang hàng", "2,6 m³")]},
    {"id": "ebus", "name": "VinFast eBus", "category": "fleet", "bodyType": "Xe buýt điện", "seats": 60, "displayPrice": "Liên hệ giải pháp vận tải", "tagline": "Thành phố chuyển động êm hơn.", "specs": [("Dung lượng pin", "359–422 kWh"), ("Sức chứa", "60–90")]} ,
]

_VEHICLE_MEDIA_EXTENSIONS = {
    "vf3": "png",
    "vf6": "png",
    "vf-mpv-7": "png",
    "vf9": "png",
    "herio-green": "png",
    "nerio-green": "png",
}

# All 14 files published under /media/vehicles/<id>/studio.* have a verified
# alpha channel. Keep one truthful presentation mode so BookingTicket, the car
# switcher and catalogue never wrap Limo Green/eBus in a fake white photo card.
_VEHICLE_STUDIO_MODES: dict[str, str] = {}


for order, vehicle in enumerate(_VEHICLES, start=1):
    slug = vehicle["id"]
    media_extension = _VEHICLE_MEDIA_EXTENSIONS.get(slug, "webp")
    short_specs = [{"label": label, "value": value} for label, value in vehicle.pop("specs")]
    first_spec_label = short_specs[0]["label"] if short_specs else "Quãng đường tham chiếu"
    first_spec_val = short_specs[0]["value"] if short_specs else "Đang cập nhật"
    range_fact = {"label": first_spec_label, "value": first_spec_val}
    charging_fact = {"label": "Sạc nhanh 10–70%", "value": "30 phút"}
    # PHẢI để rỗng — đừng gán cứng bộ màu mặc định vào đây lần nữa.
    # Bảng màu thật của từng mẫu nằm ở _COLORS_BY_VEHICLE bên dưới và đi ra qua endpoint chi
    # tiết (xem chỗ gán detail["colors"]). Gán trắng/đen/xanh cho cả 14 mẫu ở đây gây hai hậu quả:
    #   1. Sai sự thật — VF 3 thật ra là Xám Zenith Grey / Hồng Rose Pink / Đỏ Crimson Red.
    #   2. Chặn luôn bảng màu bổ sung bên frontend (data/vehicle-colors.js), vì bảng đó chỉ
    #      nhảy vào khi backend trả RỖNG. Có 3 màu giả là nó không bao giờ nhảy vào nữa.
    # Dải xe ngoài trang chủ tự gọi endpoint chi tiết để lấy màu thật, nên để rỗng là đúng.
    color_options: list[dict[str, Any]] = []
    vehicle.update(
        navName=vehicle["name"],
        thumbnail=_media(f"/media/vehicles/{slug}/thumbnail.{media_extension}", vehicle["name"], focalPoint="50% 50%"),
        studioImage={
            "url": f"/media/vehicles/{slug}/studio.{media_extension}",
            "mode": _VEHICLE_STUDIO_MODES.get(slug, "cutout"),
        },
        shortSpecs=short_specs,
        range=range_fact,
        charging=charging_fact,
        colorOptions=color_options,
        featured=vehicle["category"] == "personal",
        testDriveEligible=slug not in {"ec-van", "ebus"},
        sortOrder=order * 10,
        revision=REVISION,
    )


_DETAILS: dict[str, dict[str, Any]] = {
    vehicle["id"]: {
        "description": vehicle["tagline"],
        "brochure": {"title": f"Thông tin sản phẩm {vehicle['name']}", "url": f"/media/brochures/{vehicle['id']}.pdf", "revision": REVISION},
        "specifications": [{"group": "Thông số chính", "items": deepcopy(vehicle["shortSpecs"])}],
        "colors": vehicle["colorOptions"],
        "chapters": [
            {"id": "exterior", "title": "Ngoại thất", "sectionKey": "exterior"},
            {"id": "interior", "title": "Nội thất", "sectionKey": "interior"},
            {"id": "technology", "title": "Công nghệ", "sectionKey": "technology"},
        ],
        "gallery": [
            {"id": f"{vehicle['id']}-ext-1", "sectionKey": "exterior", "title": "Góc đầu xe", "url": vehicle["studioImage"]["url"], "focalPoint": "50% 50%", "aspectRatio": "16 / 10", "fit": "cover", "sortOrder": 10},
            {"id": f"{vehicle['id']}-int-1", "sectionKey": "interior", "title": "Khoang lái", "url": vehicle["thumbnail"]["url"], "focalPoint": "50% 50%", "aspectRatio": "16 / 10", "fit": "cover", "sortOrder": 20},
        ],
        "actionMedia": None,
        "presentationFilm": {"sectionKey": "interior", "url": "/media/presentation.mp4"},
        "motion": {"imageUrl": vehicle["studioImage"]["url"], "preset": "horizontal", "focalPoint": "50% 50%"},
    }
    for vehicle in _VEHICLES
}

for vehicle_id in ("vf8", "vf8-the-he-moi", "vf9"):
    extension = _VEHICLE_MEDIA_EXTENSIONS.get(vehicle_id, "webp")
    _DETAILS[vehicle_id]["presentationFilm"] = {
        "url": f"/media/vehicles/{vehicle_id}/presentation.mp4",
        "posterUrl": f"/media/vehicles/{vehicle_id}/thumbnail.{extension}",
        "mimeType": "video/mp4",
        "autoplayAllowed": True,
    }


def _vehicle_media(path: str, alt: str = "", **extra: Any) -> dict[str, Any]:
    return _media(f"/media/vehicle-media/{path}", alt, **extra)


def _color(name: str, hex_value: str, image_path: str) -> dict[str, Any]:
    return {"name": name, "hex": hex_value, "image": _vehicle_media(image_path, name)}


_CHAPTER_COPY: dict[str, tuple[str, str]] = {
    "exterior": ("Hình khối", "Tỷ lệ tổng thể và đường nét tạo nên nhận diện đầu tiên."),
    "profile": ("Đường nét bên hông", "Dáng xe nhìn ngang cho thấy tỷ lệ và chiều dài cơ sở."),
    "rear": ("Góc sau", "Cụm đèn hậu và phần đuôi hoàn thiện nhận diện của dòng xe."),
    "cockpit": ("Khoang lái", "Vô lăng, màn hình và những thao tác thường dùng nằm trong tầm với."),
    "cabin": ("Không gian hành khách", "Chỗ ngồi, vật liệu và sự thoải mái dành cho người đi cùng."),
    "rearSeats": ("Hàng ghế sau", "Chỗ ngồi phía sau và không gian dành cho hành khách đường dài."),
    "technology": ("Cấu trúc kỹ thuật", "Bố trí pin, khung gầm và hệ truyền động bên dưới thân xe."),
    "drive": ("Trên đường", "Chiếc xe trong bối cảnh vận hành thực tế."),
    "charging": ("Nạp năng lượng", "Giải pháp sạc đi kèm cho những hành trình dài."),
    "cargo": ("Khoang hàng", "Không gian chở hàng và khả năng xoay trở khi giao vận."),
}


def _chapter(kind: str, image_path: str, tone: str = "dark") -> dict[str, Any]:
    title, copy = _CHAPTER_COPY[kind]
    return {"key": kind, "title": title, "copy": copy, "tone": tone, "media": _vehicle_media(image_path, title)}


_COLORS_BY_VEHICLE: dict[str, list[dict[str, Any]]] = {
    "vf3": [
        _color("Xám Zenith Grey", "#909396", "VF3/xám.png"),
        _color("Hồng Rose Pink", "#d9a2ad", "VF3/hồng.png"),
        _color("Đỏ Crimson Red", "#a3232d", "VF3/đỏ.png"),
    ],
    "vf5": [
        _color("Trắng Infinity Blanc", "#ecece8", "VF5/trắng.webp"),
        _color("Vàng Summer Yellow · nóc Jet Black", "#d5ad28", "VF5/vàng đen.webp"),
        _color("Xám Zenith Grey", "#73777b", "VF5/xám.webp"),
        _color("Đỏ Solar Ruby", "#a31f2d", "VF5/đỏ.webp"),
    ],
    "vf7": [
        _color("Đen Jet Black", "#202225", "VF7/product-CE11.webp"),
        _color("Trắng Infinity Blanc", "#ecece8", "VF7/product-CE18.webp"),
        _color("Đỏ Solar Ruby", "#a90e1a", "VF7/product-CE1M.webp"),
        _color("Xám Zenith Grey", "#808489", "VF7/product-CE1V.webp"),
        _color("Xanh Urban Mint", "#87957d", "VF7/product-CE1W.webp"),
    ],
    "vf8": [
        _color("Đen Jet Black", "#202225", "VF8/product-CE11.webp"),
        _color("Trắng Brahminy White", "#ecece8", "VF8/product-CE18.webp"),
        _color("Đỏ Crimson Red", "#a91e28", "VF8/product-CE1M.webp"),
        _color("Xanh Deep Ocean", "#254538", "VF8/product-CE22.webp"),
        _color("Xám Neptune Grey · phối kim loại", "#777c82", "VF8/product-171V.webp"),
        _color("Trắng Brahminy · phối kim loại", "#e6e7e4", "VF8/product-1V18.webp"),
    ],
    "vf9": [
        _color("Đen Jet Black", "#1f2123", "VF9/CE11-cutout.webp"),
        _color("Trắng Infinity Blanc", "#ededeb", "VF9/CE18-cutout.webp"),
        _color("Xám Zenith Grey", "#7c8083", "VF9/CE1V-cutout.webp"),
        _color("Đỏ Crimson Red", "#9d2630", "VF9/CE1M-cutout.webp"),
        _color("Xanh Urban Mint", "#9aa58e", "VF9/CE1W-cutout.webp"),
        _color("Xanh Ivy Green", "#2e483d", "VF9/CE22-cutout.webp"),
        _color("Bạc Desat Silver", "#b8b9b7", "VF9/CE17-cutout.webp"),
    ],
    "herio-green": [
        _color("Trắng", "#e9e9e5", "Dịch vụ_Herio Green/trắng.png"),
        _color("Đen", "#222426", "Dịch vụ_Herio Green/Đen.png"),
        _color("Đỏ", "#94282d", "Dịch vụ_Herio Green/đỏ.png"),
    ],
}


_CHAPTERS_BY_VEHICLE: dict[str, list[dict[str, Any]]] = {
    "vf3": [_chapter("exterior", "VF3/exterior.png", "light"), _chapter("cockpit", "VF3/cockpit.jpg"), _chapter("rear", "VF3/rear.png", "light")],
    "vf5": [_chapter("exterior", "VF5/trắng.webp", "light"), _chapter("cockpit", "VF5/2.webp"), _chapter("cabin", "VF5/4.webp")],
    "vf6": [_chapter("exterior", "VF6/vf6-front-model-cutout.png", "light"), _chapter("cockpit", "VF6/interior-vf6-2.jpg"), _chapter("technology", "VF6/technology-vf6-3.jpg", "light")],
    "vf7": [_chapter("drive", "VF7/vf7-uu-diem-3.webp"), _chapter("cockpit", "VF7/vf7-noi-that-compare-left.webp"), _chapter("cabin", "VF7/vf7-noi-that-overview.webp")],
    "vf-mpv-7": [_chapter("exterior", "VF7 FMP/vf-mpv-7-model-cutout.png", "light"), _chapter("cabin", "VF7 FMP/D_03.webp"), _chapter("cockpit", "VF7 FMP/D_05.webp")],
    "vf8": [_chapter("drive", "VF8/banner.webp"), _chapter("cockpit", "VF8/volang.webp"), _chapter("cabin", "VF8/gheda-vegan.webp")],
    "vf8-the-he-moi": [_chapter("drive", "VF8 All the new/car-left.webp"), _chapter("cockpit", "VF8 All the new/ex-right.webp"), _chapter("cabin", "VF8 All the new/ex-ex5-e.png", "light")],
    "vf9": [_chapter("charging", "VF9/charging-tag-line-bg.webp"), _chapter("cockpit", "VF9/int-slide-1.webp"), _chapter("rearSeats", "VF9/int-slide-4.webp")],
    "herio-green": [_chapter("drive", "Dịch vụ_Herio Green/herio-green-section-3-3.webp"), _chapter("cockpit", "Dịch vụ_Herio Green/parallax-4.webp"), _chapter("rearSeats", "Dịch vụ_Herio Green/parallax-1.webp")],
    "minio-green": [_chapter("rear", "Dịch vụ_MINIO Green/feature-exterior@2x.webp", "light"), _chapter("cockpit", "Dịch vụ_MINIO Green/interior-gallery-left@2x.webp", "light"), _chapter("rearSeats", "Dịch vụ_MINIO Green/interior-gallery-right@2x.webp", "light")],
    "nerio-green": [_chapter("exterior", "Dịch vụ_Nerio Green/nerio-img-04.webp", "light"), _chapter("profile", "Dịch vụ_Nerio Green/nerio-img-11.webp", "light"), _chapter("rear", "Dịch vụ_Nerio Green/nerio-img-06.webp", "light")],
    "limo-green": [_chapter("exterior", "Dịch vụ_Limo Green/limo-green-studio.webp"), _chapter("cockpit", "Dịch vụ_Limo Green/img_slider.webp"), _chapter("cabin", "Dịch vụ_Limo Green/limo-green-5.webp")],
    "ec-van": [_chapter("exterior", "Dịch vụ_ EC Van/ecvan-jade.webp", "light"), _chapter("cargo", "Dịch vụ_ EC Van/ecvan-img-04.webp", "light"), _chapter("drive", "Dịch vụ_ EC Van/ecvan-banner-01.webp")],
    "ebus": [_chapter("drive", "Dịch vụ_EBus/ebus-img-01.webp"), _chapter("cabin", "Dịch vụ_EBus/ebus-img-03.webp")],
}


_GALLERY_BY_VEHICLE: dict[str, list[str]] = {
    "vf3": ["VF3/2.png", "VF3/exterior.png", "VF3/cockpit.jpg", "VF3/rear.png", "VF3/xám.png", "VF3/hồng.png", "VF3/đỏ.png"],
    "vf5": ["VF5/2.webp", "VF5/3.webp", "VF5/4.webp", "VF5/5.webp", "VF5/trắng.webp", "VF5/vàng đen.webp", "VF5/xám.webp", "VF5/đỏ.webp"],
    "vf6": ["VF6/VF6-Lifestyle-10.webp", "VF6/interior-vf6-1.jpg", "VF6/interior-vf6-2.jpg", "VF6/technology-vf6-3.jpg", "VF6/technology-vf6-4.jpg"],
    "vf7": ["VF7/vf7-passion.webp", "VF7/vf7-noi-that-overview.webp", "VF7/vf7-uu-diem-1.webp", "VF7/vf7-uu-diem-3.webp", "VF7/vf7-noi-that-compare-left.webp", "VF7/vf7-noi-that-compare-right.webp", "VF7/product-CE18.webp"],
    "vf-mpv-7": ["VF7 FMP/D_01.webp", "VF7 FMP/D_02.webp", "VF7 FMP/D_03.webp", "VF7 FMP/D_04.webp", "VF7 FMP/D_05.webp"],
    "vf8": ["VF8/banner.webp", "VF8/interior-img1.webp", "VF8/ai.webp", "VF8/hud.webp", "VF8/volang.webp", "VF8/gheda-vegan.webp", "VF8/product-CE18.webp"],
    "vf8-the-he-moi": ["VF8 All the new/VF8PH-13.webp", "VF8 All the new/car-left.webp", "VF8 All the new/tech-t1.png", "VF8 All the new/ex-right.webp", "VF8 All the new/ex-ex5-e.png"],
    "vf9": ["VF9/interior-first-sight.webp", "VF9/int-slide-1.webp", "VF9/int-slide-2.webp", "VF9/int-slide-4.webp", "VF9/cs-home-charger.webp", "VF9/CE18.webp"],
    "herio-green": ["Dịch vụ_Herio Green/herio-green-section-3-1.webp", "Dịch vụ_Herio Green/herio-green-section-3-3.webp", "Dịch vụ_Herio Green/parallax-1.webp", "Dịch vụ_Herio Green/parallax-4.webp", "Dịch vụ_Herio Green/trắng.png"],
    "minio-green": ["Dịch vụ_MINIO Green/feature-exterior@2x.webp", "Dịch vụ_MINIO Green/feature-interior@2x.webp", "Dịch vụ_MINIO Green/gallery-featured-img3.webp", "Dịch vụ_MINIO Green/interior-gallery-left@2x.webp", "Dịch vụ_MINIO Green/interior-gallery-right@2x.webp"],
    "nerio-green": ["Dịch vụ_Nerio Green/nerio-img-01.webp", "Dịch vụ_Nerio Green/nerio-img-04.webp", "Dịch vụ_Nerio Green/nerio-img-06.webp", "Dịch vụ_Nerio Green/nerio-img-09.webp", "Dịch vụ_Nerio Green/nerio-img-11.webp"],
    "limo-green": ["Dịch vụ_Limo Green/img_slider.webp", "Dịch vụ_Limo Green/limo-green-3.webp", "Dịch vụ_Limo Green/limo-green-4.webp", "Dịch vụ_Limo Green/limo-green-5.webp"],
    "ec-van": ["Dịch vụ_ EC Van/ecvan-img-01.webp", "Dịch vụ_ EC Van/ecvan-img-03.webp", "Dịch vụ_ EC Van/ecvan-img-04.webp", "Dịch vụ_ EC Van/ecvan-jade-02.webp", "Dịch vụ_ EC Van/ecvan-banner-01.webp"],
    "ebus": ["Dịch vụ_EBus/ebus-img-01.webp", "Dịch vụ_EBus/ebus-img-02.webp", "Dịch vụ_EBus/ebus-img-03.webp", "Dịch vụ_EBus/ebus-img-05.webp"],
}


_DESCRIPTIONS_BY_VEHICLE: dict[str, str] = {
    "vf3": "Gọn để xoay trở trong phố, đủ khác biệt để mỗi hành trình mang dấu ấn riêng.",
    "vf5": "Một chiếc SUV điện linh hoạt với không gian đủ dùng cho gia đình và nhịp vận hành đô thị.",
    "vf6": "Tỷ lệ thân xe chắc gọn, nội thất tập trung vào người lái và lực kéo đến ngay khi cần.",
    "vf7": "Một hình khối fastback táo bạo, khoang lái hướng người dùng và hiệu năng hai cầu ở bản Plus AWD.",
    "vf-mpv-7": "Không gian ba hàng ghế linh hoạt, chiều dài cơ sở 2.840 mm và hệ dẫn động cầu trước cho những hành trình gia đình thoải mái hơn.",
    "vf8": "Không gian gia đình rộng rãi, hệ dẫn động AWD toàn thời gian và hệ thống hỗ trợ lái toàn diện.",
    "vf8-the-he-moi": "Cấu hình cầu trước gọn nhẹ, pin 60,13 kWh và giao diện cabin tập trung vào nhu cầu sử dụng hàng ngày.",
    "vf9": "SUV điện cỡ lớn với ba hàng ghế, dẫn động AWD và khoang hành khách được thiết kế cho những chuyến đi dài.",
    "herio-green": "Thiết kế tối ưu cho tần suất vận hành cao, khoang hành khách thoáng và chi phí năng lượng dễ kiểm soát.",
    "minio-green": "Chiếc xe nhỏ nhất dải Green, ưu tiên bán kính vận hành đô thị và mức tiêu thụ năng lượng thấp.",
    "nerio-green": "Dòng xe dịch vụ hướng đến đội xe cần khoang hành khách dễ sử dụng và khả năng vận hành liên tục.",
    "limo-green": "Thân xe dài, ba hàng ghế và tầm hoạt động phù hợp cho vận chuyển hành khách đường dài.",
    "ec-van": "Khoang hàng 2,6 m³, bán kính quay vòng 4,85 m và hệ dẫn động cầu sau cho nhịp giao vận đô thị.",
    "ebus": "Nền tảng xe buýt điện cho vận tải công cộng với cấu hình chiều dài và sức chứa theo nhu cầu vận hành.",
}


_DETAIL_SPECS_BY_VEHICLE: dict[str, list[tuple[str, str]]] = {
    "vf3": [("Quãng đường NEDC", "215 km"), ("Công suất tối đa", "32 kW"), ("Sạc nhanh 10-70%", "36 phút"), ("Khoảng sáng gầm", "191 mm")],
    "vf5": [("Quãng đường NEDC", "326 km"), ("Công suất tối đa", "100 kW"), ("Mô-men xoắn", "135 Nm"), ("Pin khả dụng", "37,23 kWh")],
    "vf6": [("Quãng đường NEDC", "460 km"), ("Công suất tối đa", "150 kW"), ("Mô-men xoắn", "310 Nm"), ("Pin khả dụng", "59,6 kWh")],
    "vf7": [("Quãng đường WLTP", "431 km"), ("Công suất bản Plus", "260 kW"), ("Mô-men xoắn bản Plus", "500 Nm"), ("Dẫn động bản Plus", "AWD")],
    "vf-mpv-7": [("Quãng đường NEDC", "450 km"), ("Công suất tối đa", "150 kW"), ("Mô-men xoắn cực đại", "280 Nm"), ("Pin khả dụng", "60,13 kWh")],
    "vf8": [("Quãng đường bản Eco", "420 km"), ("Công suất bản Plus", "300 kW"), ("Mô-men xoắn bản Plus", "620 Nm"), ("Pin khả dụng", "82 kWh")],
    "vf8-the-he-moi": [("Quãng đường NEDC", "480-500 km"), ("Công suất tối đa", "170 kW"), ("Mô-men xoắn", "330 Nm"), ("Pin khả dụng", "60,13 kWh")],
    "vf9": [("Quãng đường WLTP Eco", "626 km"), ("Công suất tối đa", "300 kW"), ("Mô-men xoắn", "620 Nm"), ("Pin khả dụng", "123 kWh")],
    "herio-green": [("Quãng đường NEDC", "326 km"), ("Công suất tối đa", "100 kW"), ("Sức chứa", "5 chỗ"), ("Dẫn động", "FWD")],
    "minio-green": [("Quãng đường NEDC", "210 km"), ("Công suất tối đa", "30 kW"), ("Mô-men xoắn", "65 Nm"), ("Pin khả dụng", "18,3 kWh")],
    "nerio-green": [("Quãng đường tham chiếu", "318 km"), ("Công suất tối đa", "110 kW"), ("Sức chứa", "5 chỗ"), ("Dẫn động", "FWD")],
    "limo-green": [("Quãng đường NEDC", "450 km"), ("Công suất tối đa", "150 kW"), ("Mô-men xoắn", "280 Nm"), ("Pin khả dụng", "60,13 kWh")],
    "ec-van": [("Quãng đường NEDC", "175 km"), ("Công suất tối đa", "30 kW"), ("Khoang hàng", "2,6 m³"), ("Pin khả dụng", "18,3 kWh")],
    "ebus": [("Chiều dài thân xe", "8,61-12,11 m"), ("Dung lượng pin", "359-422 kWh"), ("Công suất sạc", "120-140 kW"), ("Sức chứa hành khách", "60-90")],
}


_ACTION_MEDIA_BY_VEHICLE: dict[str, str] = {
    "vf3": "VF3/2.png",
    "vf5": "VF5/1.webp",
    "vf6": "VF6/VF6-Lifestyle-12.webp",
    "vf7": "VF7/vf7-slide-in-croped.webp",
    "vf-mpv-7": "VF7 FMP/D_01.webp",
    "vf8": "VF8/banner.webp",
    "vf8-the-he-moi": "VF8 All the new/VF8PH-23.webp",
    "vf9": "VF9/img-video.webp",
    "herio-green": "Dịch vụ_Herio Green/Hero-new.webp",
    "minio-green": "Dịch vụ_MINIO Green/Minio.webp",
    "nerio-green": "Dịch vụ_Nerio Green/nerio-img-01.webp",
    "limo-green": "Dịch vụ_Limo Green/footer.webp",
    "ec-van": "Dịch vụ_ EC Van/ecvan-banner-01.webp",
    "ebus": "Dịch vụ_EBus/ebus-img-01.webp",
}


_PRESENTATION_COPY: dict[str, dict[str, str]] = {
    "vf8": {
        "eyebrow": "VF 8 trong chuyển động",
        "title": "Ánh sáng đi qua từng bề mặt.",
        "copy": "Một thước phim liền mạch để quan sát tỷ lệ, đường vai và dấu ấn ngoại thất của VF 8 khi chiếc xe thực sự chuyển động.",
    },
    "vf8-the-he-moi": {
        "eyebrow": "Một nhịp nhìn mới",
        "title": "Tinh giản, nhưng không đứng yên.",
        "copy": "Chuyển động điện ảnh làm nổi bật cách bề mặt và ánh sáng định hình diện mạo VF 8 Thế hệ mới.",
    },
    "vf9": {
        "eyebrow": "Bên trong VF 9",
        "title": "Khoang lái mở ra trong một nhịp phim.",
        "copy": "Góc máy đi từ vị trí người lái qua màn hình trung tâm, cho cảm nhận trực tiếp hơn về cách các chi tiết được đặt trong tầm quan sát.",
    },
}


for vehicle_id, detail in _DETAILS.items():
    chapters = deepcopy(_CHAPTERS_BY_VEHICLE.get(vehicle_id, []))
    gallery_paths = _GALLERY_BY_VEHICLE.get(vehicle_id, [])
    detail_specs = _DETAIL_SPECS_BY_VEHICLE.get(vehicle_id)
    detail["description"] = _DESCRIPTIONS_BY_VEHICLE.get(vehicle_id, detail["description"])
    if detail_specs:
        detail["specifications"] = [
            {"group": "Thông số chính", "items": [{"label": label, "value": value} for label, value in detail_specs]},
        ]
    detail["colors"] = deepcopy(_COLORS_BY_VEHICLE.get(vehicle_id, []))
    detail["chapters"] = chapters
    detail["gallery"] = [
        _vehicle_media(path, f"{vehicle_id} gallery {index:02d}")
        for index, path in enumerate(gallery_paths, start=1)
    ]
    if vehicle_id in _ACTION_MEDIA_BY_VEHICLE:
        detail["actionMedia"] = _vehicle_media(_ACTION_MEDIA_BY_VEHICLE[vehicle_id], f"{vehicle_id} action")
    if detail["presentationFilm"] and vehicle_id in _PRESENTATION_COPY:
        detail["presentationFilm"].update(_PRESENTATION_COPY[vehicle_id])


_CONTENT: dict[str, dict[str, Any]] = {
    "home": {
        "revision": REVISION,
        "hero": {"eyebrow": "VinFast", "title": "Cùng bạn bứt phá mọi giới hạn", "copy": "Hệ sinh thái di chuyển điện thông minh.", "vehicleId": "vf7", "media": _media("/media/content/home/hero.webp", "Dải xe điện VinFast", focalPoint="50% 50%")},
        "stories": [],
        "testimonials": [
            {
                "quote": "Điều thuyết phục tôi không phải một con số đơn lẻ, mà là cảm giác chiếc xe phản hồi ngay và cabin vẫn yên tĩnh giữa giờ cao điểm.",
                "name": "Nguyễn Khánh Linh",
                "role": "Khách hàng VF 7 · TP. Hồ Chí Minh",
            },
            {
                "quote": "Tôi thử xe cùng cả gia đình. Chỉ sau một vòng lái, mọi người đã biết hàng ghế nào sẽ là chỗ quen thuộc của mình.",
                "name": "Trần Hoàng Phúc",
                "role": "Khách hàng VF 9 · Hà Nội",
            },
            {
                "quote": "Lịch thử xe được giữ đúng mẫu và đúng khung giờ. Tôi đến showroom, nhận xe và bắt đầu lái mà không phải chờ.",
                "name": "Lê Ngọc An",
                "role": "Khách hàng VF 6 · Đà Nẵng",
            },
        ],
        "sections": [{"id": "factory", "type": "mediaFeature", "title": "Năng lực sản xuất", "copy": "Công nghệ và quy trình sản xuất hiện đại.", "media": _media("/media/content/home/factory.jpg", "Nhà máy VinFast")}],
    },
    "charging": {
        "revision": REVISION,
        "hero": {"title": "Pin và trạm sạc", "copy": "Hạ tầng sạc cho hành trình liền mạch.", "media": _media("/media/content/charging/hero.webp", "Trạm sạc VinFast")},
        "network": {"title": "Mạng lưới sạc toàn quốc", "copy": "Các điểm sạc được phát triển tại nhiều tỉnh thành."},
        "chargingUnits": [
            {"power": "250 kW", "name": "Sạc siêu nhanh DC", "image": _media("/media/content/charging/250kw.png", "Trụ sạc 250 kW tách nền"), "facts": ["Tủ đứng", "1 cổng / trụ", "200–1.000 VDC", "IP54"]},
            {"power": "150 kW", "name": "Sạc siêu nhanh DC", "image": _media("/media/content/charging/150kw.png", "Trụ sạc 150 kW tách nền"), "facts": ["Tủ đứng", "2 cổng / trụ", "200–1.000 VDC", "IP54"]},
            {"power": "60 kW", "name": "Sạc nhanh DC", "image": _media("/media/content/charging/60kw.png", "Trụ sạc 60 kW tách nền"), "facts": ["Tủ đứng", "2 cổng / trụ", "200–1.000 VDC", "IP54"]},
            {"power": "30 kW", "name": "Sạc nhanh DC", "image": _media("/media/content/charging/30kw.png", "Trụ sạc 30 kW tách nền"), "facts": ["Treo tường hoặc tủ đứng", "1 cổng / trụ", "CAN Protocol", "IP54"]},
        ],
        "guideMedia": [], "brochure": {"title": "Dịch vụ pin ô tô điện", "url": "/media/brochures/charging.pdf", "revision": REVISION},
    },
    "after-sales": {
        "revision": REVISION, "effectiveAt": "2026-08-04T00:00:00+07:00",
        "hero": {"title": "Dịch vụ hậu mãi", "copy": "Đồng hành trong suốt vòng đời xe.", "media": _media("/media/content/after-sales/hero.webp", "Dịch vụ hậu mãi VinFast")},
        "warrantyTables": [
            {"term": "10 năm", "distance": "200.000 km", "models": "VF 8, VF 9, Lạc Hồng 900 LX"},
            {"term": "8 năm", "distance": "160.000 km", "models": "VF 3, VF 5, VF 6, VF 7, VF Minio Green, VF Herio Green, VF MPV 7, VF Nerio Green, VF Limo Green"},
            {"term": "7 năm", "distance": "160.000 km", "models": "VF EC Van"},
        ],
        "policies": [], "consultationMedia": _media("/media/content/after-sales/consultation.webp", "Tư vấn dịch vụ"),
        "brochure": {"title": "Chính sách bảo hành ô tô", "url": "/media/brochures/warranty.pdf", "revision": REVISION},
    },
}


class SiteCatalogService:
    def __init__(self, snapshot_path: Path | None = None, media_base_url: str | None = None) -> None:
        self._vehicles = deepcopy(_VEHICLES)
        self._details = deepcopy(_DETAILS)
        self._content = deepcopy(_CONTENT)
        self._media_base_url = (media_base_url or get_settings().media_base_url).rstrip("/")
        configured_path = snapshot_path or Path(os.getenv("SITE_CATALOG_PATH", "data/site_catalog.json"))
        if configured_path.is_file():
            self.import_snapshot(configured_path)

    def list_vehicles(self, *, category: str | None, featured: bool | None, test_drive_eligible: bool | None, limit: int) -> list[dict[str, Any]]:
        vehicles = self._vehicles
        if category is not None:
            vehicles = [item for item in vehicles if item["category"] == category]
        if featured is not None:
            vehicles = [item for item in vehicles if item["featured"] is featured]
        if test_drive_eligible is not None:
            vehicles = [item for item in vehicles if item["testDriveEligible"] is test_drive_eligible]
        return self._with_public_media_urls(deepcopy(sorted(vehicles, key=lambda item: item["sortOrder"])[:limit]))

    def get_vehicle(self, vehicle_id: str) -> dict[str, Any] | None:
        summary = next((item for item in self._vehicles if item["id"] == vehicle_id), None)
        result = None if summary is None else {**deepcopy(summary), **deepcopy(self._details[vehicle_id])}
        return self._with_public_media_urls(result)

    def get_content(self, page: str) -> dict[str, Any] | None:
        content = self._content.get(page)
        return self._with_public_media_urls(deepcopy(content)) if content is not None else None

    def _with_public_media_urls(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._with_public_media_urls(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._with_public_media_urls(item) for item in value]
        if isinstance(value, str) and value.startswith("/media/"):
            return f"{self._media_base_url}/{value.removeprefix('/media/')}"
        return value

    def snapshot(self) -> dict[str, Any]:
        return {"vehicles": deepcopy(self._vehicles), "details": deepcopy(self._details), "content": deepcopy(self._content)}

    def import_snapshot(self, source: Path, destination: Path | None = None) -> dict[str, int]:
        """Validate a CMS export and optionally publish normalized JSON atomically."""
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            snapshot = CatalogSnapshot.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Invalid site catalog snapshot: {exc}") from exc

        vehicle_ids = {item.id for item in snapshot.vehicles}
        if set(snapshot.details) != vehicle_ids:
            raise ValueError("Snapshot details must contain exactly one record for every vehicle")
        if not {"home", "charging", "after-sales"}.issubset(snapshot.content):
            raise ValueError("Snapshot is missing one or more required content pages")

        normalized = snapshot.model_dump(mode="json", by_alias=True)
        self._vehicles = normalized["vehicles"]
        self._details = normalized["details"]
        self._content = normalized["content"]
        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(f"{destination.suffix}.tmp")
            temporary.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(destination)
        return {"vehicles": len(self._vehicles), "contentPages": len(self._content)}

    @staticmethod
    def etag(value: Any) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return f'"{sha256(encoded).hexdigest()}"'


site_catalog_service = SiteCatalogService()
