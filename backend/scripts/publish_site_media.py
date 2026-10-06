"""Copy frontend fallback images into the backend local media origin.

Production should upload the same destination keys to object storage/CDN.
Usage: python scripts/publish_site_media.py [frontend_root] [media_root]
"""

import os
import shutil
import sys
from pathlib import Path

VEHICLES = {
    "vf3": "src/media/local/vehicle-media/VF3/xám.webp",
    "vf5": "src/media/local/vehicle-media/VF5/trắng.webp",
    "vf6": "src/media/local/by-model/vf6/studio.png",
    "vf7": "src/media/local/vehicle-media/VF7/product-CE18.webp",
    "vf-mpv-7": "src/media/local/by-model/vf-mpv-7/studio.png",
    "vf8": "src/media/local/vehicle-media/VF8/product-CE18.webp",
    "vf8-the-he-moi": "src/media/local/vehicle-media/VF8 All the new/VF8PH-23.webp",
    "vf9": "src/media/local/common/vf9-studio.png",
    "herio-green": "src/media/local/vehicle-media/Dịch vụ_Herio Green/trắng.webp",
    "minio-green": "src/media/local/vehicle-media/Dịch vụ_MINIO Green/Minio.webp",
    "nerio-green": "src/media/local/common/nerio-green-studio.png",
    "limo-green": "src/media/local/by-model/limo-green/studio.webp",
    "ec-van": "src/media/local/vehicle-media/Dịch vụ_ EC Van/ecvan-jade.webp",
    "ebus": "src/media/local/by-model/ebus/studio.webp",
}

CONTENT = {
    "content/home/hero.webp": "src/media/local/common/vinfast-road-banner.webp",
    "content/home/factory.jpg": "src/media/local/vehicle-media/nha-may-vinfast.jpg",
    "content/after-sales/hero.webp": "src/media/local/common/after-sales-hero.webp",
    "content/after-sales/consultation.webp": "src/media/local/common/after-sales-consultation.webp",
    "content/charging/hero.webp": "src/media/local/vehicle-media/Trạm sạc/pin-tramsac-6_1660273722.png.webp",
    "content/charging/250kw.png": "src/media/local/vehicle-media/Trạm sạc/charger-250-cutout-v2.png",
    "content/charging/150kw.png": "src/media/local/vehicle-media/Trạm sạc/charger-150-cutout-v2.png",
    "content/charging/60kw.png": "src/media/local/vehicle-media/Trạm sạc/charger-60-cutout-v2.png",
    "content/charging/30kw.png": "src/media/local/vehicle-media/Trạm sạc/charger-30-cutout-v2.png",
    # Ảnh chìm của thư mã xác thực. Nó KHÔNG nằm dưới vehicle-media vì không gắn
    # với mẫu xe nào, mà lệnh copytree bên dưới chỉ chép vehicle-media, nên phải
    # khai riêng ở đây. Thiếu dòng này thì máy nào cài mới cũng mất ảnh chìm thư
    # mã xác thực, và mất im lặng: thư vẫn gửi, chỉ là card trơ nền tối.
    "email/lac-hong-watermark.jpg": "src/media/local/email/lac-hong-watermark.jpg",
}

COMMON_TO_VEHICLE_MEDIA = {
    "VF6/vf6-front-model-cutout.png": "src/media/local/common/vf6-front-model-cutout.png",
    "VF7 FMP/vf-mpv-7-model-cutout.png": "src/media/local/common/vf-mpv-7-model-cutout.png",
    "Dịch vụ_Limo Green/limo-green-studio.webp": "src/media/local/common/limo-green-studio.webp",
}

# Cloudflare blocks object keys containing path-like double dots. Keep the
# original frontend files untouched, but publish stable CDN-safe aliases.
SAFE_VEHICLE_MEDIA_ALIASES = {
    "VF3/1..webp": "VF3/1.webp",
    "VF3/2..webp": "VF3/exterior.webp",
    "VF3/3..webp": "VF3/cockpit.webp",
    "VF3/4..webp": "VF3/rear.webp",
    "VF5/1..webp": "VF5/1.webp",
    "VF5/3..webp": "VF5/3.webp",
    "VF5/4..webp": "VF5/4.webp",
    "VF5/5..webp": "VF5/5.webp",
}

VIDEOS = {
    "vf8": "src/media/local/vehicle-media/VF8/VF8.mp4",
    "vf8-the-he-moi": "src/media/local/vehicle-media/VF8 All the new/VF8.mp4",
    "vf9": "src/media/local/vehicle-media/VF9/VF9.mp4",
}

BROCHURES = {
    "vf5": "src/media/local/brochures/VFVN_VF 5_Brochure Bản sửa 290126_1333PM.pdf",
    "vf6": "src/media/local/brochures/VF6_Brochure.pdf",
    "vf7": "src/media/local/brochures/VF7_Brochure.pdf",
    "vf8": "src/media/local/brochures/VF8Brochure.pdf",
    "vf8-the-he-moi": "src/media/local/brochures/VF 8 The he moi All News_Brochure_final 20.05.pdf",
    "vf9": "src/media/local/brochures/VF 9_ Brochure.pdf",
    "herio-green": "src/media/local/brochures/Dịch vụ_Catalogue-VinFast-Herio-Green.pdf",
    "minio-green": "src/media/local/brochures/Dịch vụ_Brochure Minio Green 090126.pdf",
    "nerio-green": "src/media/local/brochures/Dịch vụ_Catalogue-VinFast-Nerio-Green.pdf",
    "limo-green": "src/media/local/brochures/Dịch  vụ_Brochure Limo Green 090126.pdf",
    "ec-van": "src/media/local/brochures/Dịch vụ_brochure-ec-van-040726-e.pdf",
    "ebus": "src/media/local/brochures/Dịch vụ_VinFast-eBus_Broschure_092025.pdf",
}

LEGACY_KEYS = [
    "content/home/factory.webp",
    "content/charging/250kw.webp",
    "content/charging/150kw.webp",
    "content/charging/60kw.webp",
    "content/charging/30kw.webp",
    *[
        f"vehicles/{vehicle_id}/{name}.webp"
        for vehicle_id in ("vf3", "vf6", "vf-mpv-7", "vf9", "herio-green", "nerio-green")
        for name in ("thumbnail", "studio")
    ],
]


def _resolve_source(source: Path) -> Path:
    if source.is_file():
        return source
    for ext in [".webp", ".png", ".jpg", ".jpeg", ".svg"]:
        candidate = source.with_suffix(ext)
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Missing source media: {source}")


def _copy(source: Path, destination: Path, optional: bool = False) -> None:
    try:
        actual_source = _resolve_source(source)
    except FileNotFoundError:
        if optional:
            return
        raise
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(actual_source, destination)


def _assert_separate_media_trees(source: Path, destination: Path) -> None:
    """Reject overlapping trees before publishing can mutate source media."""
    resolved_source = source.resolve()
    resolved_destination = destination.resolve()
    if (
        resolved_source == resolved_destination
        or resolved_source in resolved_destination.parents
        or resolved_destination in resolved_source.parents
    ):
        raise ValueError(
            "Frontend vehicle media source and publish destination must not overlap: "
            f"{resolved_source} -> {resolved_destination}"
        )


def main() -> int:
    frontend_root = Path(sys.argv[1] if len(sys.argv) > 1 else "../frontend").resolve()
    media_root = Path(sys.argv[2] if len(sys.argv) > 2 else os.getenv("MEDIA_ROOT", "data/media")).resolve()
    vehicle_media_source = frontend_root / "src" / "media" / "local" / "vehicle-media"
    vehicle_media_destination = media_root / "vehicle-media"
    _assert_separate_media_trees(vehicle_media_source, vehicle_media_destination)

    for legacy_key in LEGACY_KEYS:
        (media_root / legacy_key).unlink(missing_ok=True)
    for vehicle_id, relative_source in VEHICLES.items():
        source = frontend_root / relative_source
        extension = source.suffix.lower()
        _copy(source, media_root / "vehicles" / vehicle_id / f"thumbnail{extension}")
        _copy(source, media_root / "vehicles" / vehicle_id / f"studio{extension}")
    for destination, relative_source in CONTENT.items():
        _copy(frontend_root / relative_source, media_root / destination, optional=True)
    if vehicle_media_source.is_dir():
        shutil.copytree(vehicle_media_source, vehicle_media_destination, dirs_exist_ok=True)
    for source_key, destination_key in SAFE_VEHICLE_MEDIA_ALIASES.items():
        _copy(vehicle_media_source / source_key, vehicle_media_destination / destination_key, optional=True)
        (vehicle_media_destination / source_key).unlink(missing_ok=True)
    for destination, relative_source in COMMON_TO_VEHICLE_MEDIA.items():
        _copy(frontend_root / relative_source, vehicle_media_destination / destination, optional=True)
    for vehicle_id, relative_source in VIDEOS.items():
        _copy(frontend_root / relative_source, media_root / "vehicles" / vehicle_id / "presentation.mp4", optional=True)
    for vehicle_id, relative_source in BROCHURES.items():
        _copy(frontend_root / relative_source, media_root / "brochures" / f"{vehicle_id}.pdf", optional=True)
    total = sum(1 for path in media_root.rglob("*") if path.is_file())
    print(f"Published {total} files into {media_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
