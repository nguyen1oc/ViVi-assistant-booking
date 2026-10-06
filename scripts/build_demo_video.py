#!/usr/bin/env python3
"""Build the P-053 product demo video from the supplied screen recording."""

from __future__ import annotations

import math
import shutil
import subprocess
import textwrap
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp/source_screen_recording.mov"
BUILD_DIR = ROOT / "tmp/demo_build"
GRAPHICS_DIR = BUILD_DIR / "graphics"
SEGMENTS_DIR = BUILD_DIR / "segments"
OUTPUT_DIR = ROOT / "output/video"
OUTPUT = OUTPUT_DIR / "P-053_ViVi_Demo_BGK_HandDoodle.mp4"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
CREAM = "#F7F3E8"
INK = "#121A24"
NAVY = "#102A43"
BLUE = "#2A65E8"
CYAN = "#BFEFF3"
MINT = "#DDF3E4"
PEACH = "#F8DED3"
LILAC = "#E7DFF8"
YELLOW = "#F4C95D"
MUTED = "#5C6773"

FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_HAND = "/System/Library/Fonts/Noteworthy.ttc"
FONT_HAND_INDEX = 1


@dataclass(frozen=True)
class Card:
    name: str
    duration: float
    title: str
    body: str
    style: str = "standard"


@dataclass(frozen=True)
class Clip:
    name: str
    start: float
    end: float
    speed: float
    caption: str
    accent: str

    @property
    def duration(self) -> float:
        return (self.end - self.start) / self.speed


TIMELINE: list[Card | Clip] = [
    Card(
        "intro",
        6.5,
        "ViVi là trợ lý đặt lịch lái thử có thật.",
        "Sản phẩm giúp khách chọn đúng xe, giữ đúng giờ và chuẩn bị đầy đủ trước khi đến showroom.",
        "intro",
    ),
    Card(
        "problem",
        7.0,
        "Khách hàng không thiếu một chiếc form. Họ thiếu sự chắc chắn sau khi bấm xác nhận.",
        "ViVi biến nhu cầu thành một lịch hẹn có xe, có giờ, có showroom và có người chịu trách nhiệm.",
        "problem",
    ),
    Clip(
        "discover_catalog",
        0.0,
        9.5,
        1.6,
        "Khách hàng bắt đầu ngay từ mẫu xe mình đang quan tâm.",
        CYAN,
    ),
    Clip(
        "discover_product",
        18.5,
        38.5,
        1.8,
        "Trang sản phẩm cho khách khám phá thiết kế và thông số trước khi đặt lịch.",
        CYAN,
    ),
    Clip(
        "booking_role",
        39.0,
        49.5,
        1.25,
        "ViVi hỏi người dùng đặt cho mình hay đặt hộ để tách đúng hai hồ sơ.",
        LILAC,
    ),
    Clip(
        "booking_showroom",
        49.5,
        58.0,
        1.2,
        "Hệ thống chỉ đề xuất showroom có đúng mẫu xe lái thử và hiển thị khoảng cách trên bản đồ.",
        MINT,
    ),
    Clip(
        "booking_slot",
        58.0,
        69.5,
        1.25,
        "Người dùng chọn một khung giờ còn thật, còn hệ thống giữ chỗ để tránh hai người đặt trùng.",
        PEACH,
    ),
    Clip(
        "booking_details",
        69.5,
        86.5,
        1.55,
        "Người dùng kiểm tra xe, showroom, thời gian và thông tin cá nhân trước khi xác nhận.",
        CYAN,
    ),
    Clip(
        "booking_otp",
        86.5,
        106.0,
        1.6,
        "Mã xác thực được gửi qua thư điện tử để bảo vệ lịch hẹn và xác nhận đúng người đặt.",
        YELLOW,
    ),
    Clip(
        "booking_confirmed",
        106.0,
        121.0,
        1.35,
        "Sau khi xác thực, hệ thống sinh mã lịch và gọi tên trạng thái Đã xác nhận ngay trên giao diện.",
        MINT,
    ),
    Clip(
        "booking_ticket",
        121.0,
        132.0,
        1.6,
        "Phiếu lịch cho biết rõ xe, showroom, giờ hẹn và trạng thái hiện tại.",
        CYAN,
    ),
    Clip(
        "booking_email",
        132.0,
        165.5,
        3.0,
        "Người đặt nhận thư xác nhận gồm mã lịch, địa chỉ, thời gian và hướng dẫn chuẩn bị.",
        YELLOW,
    ),
    Card(
        "care",
        5.5,
        "Sau khi lịch được xác nhận, ViVi bắt đầu chăm sóc.",
        "Agent trả lời câu hỏi khó tìm, đưa checklist phù hợp và chỉ nói từ nguồn đã được kiểm duyệt.",
        "care",
    ),
    Clip(
        "care_family_question",
        168.0,
        201.0,
        2.5,
        "ViVi trả lời câu hỏi chuẩn bị cho buổi lái thử thay vì hỏi lại một chuỗi trường thông tin.",
        LILAC,
    ),
    Clip(
        "care_family_checklist",
        218.0,
        248.5,
        2.6,
        "ViVi đưa ra checklist trải nghiệm phù hợp với gia đình có trẻ nhỏ.",
        MINT,
    ),
    Clip(
        "manage_auth",
        248.5,
        271.0,
        2.3,
        "Khách xác thực bằng thư điện tử để mở đúng các lịch của mình.",
        YELLOW,
    ),
    Clip(
        "manage_reschedule",
        271.0,
        288.75,
        1.65,
        "Khách tự chọn giờ mới, còn hệ thống giữ chỗ trước khi cập nhật lịch.",
        PEACH,
    ),
    Card(
        "outro",
        10.5,
        "ViVi giữ cam kết từ lúc khách chọn xe đến khi bước vào showroom.",
        "Khách nhận mã lịch ngay, tự đổi hoặc hủy khi cần, còn showroom tránh được lịch trùng và liên hệ trùng.",
        "outro",
    ),
]


def run(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    subprocess.run(command, check=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def hand_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_HAND, size, index=FONT_HAND_INDEX)


def add_paper_texture(canvas: Image.Image, seed: int) -> None:
    rng = np.random.default_rng(seed)
    texture = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(texture)
    for _ in range(1250):
        x = int(rng.integers(0, WIDTH))
        y = int(rng.integers(0, HEIGHT))
        alpha = int(rng.integers(5, 14))
        shade = int(rng.integers(88, 142))
        draw.ellipse((x, y, x + 1, y + 1), fill=(shade, shade - 8, shade - 18, alpha))
    canvas.alpha_composite(texture)


def doodle_box(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    fill: str | tuple[int, int, int, int],
    seed: int,
    width: int = 4,
    shadow: bool = True,
) -> None:
    if shadow:
        shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow_layer).rounded_rectangle(
            (box[0] + 9, box[1] + 11, box[2] + 9, box[3] + 11),
            radius=radius,
            fill=(24, 28, 30, 34),
        )
        canvas.alpha_composite(shadow_layer.filter(ImageFilter.GaussianBlur(12)))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=INK, width=width)
    rng = np.random.default_rng(seed)
    dx = int(rng.integers(-2, 3))
    dy = int(rng.integers(-2, 3))
    draw.rounded_rectangle(
        (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy),
        radius=radius,
        outline=(18, 24, 31, 125),
        width=1,
    )


def doodle_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str,
    width: int,
    seed: int,
    amplitude: float = 3.0,
) -> None:
    rng = np.random.default_rng(seed)
    points: list[tuple[int, int]] = []
    count = 32
    for index in range(count + 1):
        ratio = index / count
        x = start[0] + (end[0] - start[0]) * ratio
        y = start[1] + (end[1] - start[1]) * ratio
        wobble = math.sin(ratio * math.pi * 4.0) * amplitude + float(rng.normal(0.0, 0.7))
        points.append((int(x), int(y + wobble)))
    draw.line(points, fill=color, width=width, joint="curve")


def doodle_blob(
    canvas: Image.Image,
    center: tuple[int, int],
    radii: tuple[int, int],
    fill: str,
    seed: int,
) -> None:
    rng = np.random.default_rng(seed)
    points: list[tuple[int, int]] = []
    for index in range(72):
        angle = 2.0 * math.pi * index / 72.0
        jitter = 1.0 + float(rng.normal(0.0, 0.025))
        x = center[0] + math.cos(angle) * radii[0] * jitter
        y = center[1] + math.sin(angle) * radii[1] * jitter
        points.append((int(x), int(y)))
    draw = ImageDraw.Draw(canvas)
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=INK, width=3, joint="curve")


def rounded_shadow(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    fill: str | tuple[int, int, int, int],
    shadow_offset: tuple[int, int] = (0, 12),
    shadow_blur: int = 24,
) -> None:
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    sx, sy = shadow_offset
    shadow_draw.rounded_rectangle(
        (box[0] + sx, box[1] + sy, box[2] + sx, box[3] + sy),
        radius=radius,
        fill=(17, 26, 36, 52),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(shadow_blur)))
    ImageDraw.Draw(canvas).rounded_rectangle(box, radius=radius, fill=fill)


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, bold: bool) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > 28:
        candidate = font(size, bold)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
        size -= 2
    return font(size, bold)


def wrap_by_width(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=selected_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def paste_contained(canvas: Image.Image, source_path: Path, box: tuple[int, int, int, int]) -> None:
    source = Image.open(source_path).convert("RGBA")
    box_width = box[2] - box[0]
    box_height = box[3] - box[1]
    source.thumbnail((box_width, box_height), Image.Resampling.LANCZOS)
    x = box[0] + (box_width - source.width) // 2
    y = box[1] + (box_height - source.height) // 2
    canvas.alpha_composite(source, (x, y))


def create_caption_overlay(path: Path, caption: str, accent: str) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    box = (50, 26, 1780, 188)
    doodle_box(canvas, box, 24, (255, 253, 246, 241), seed=sum(ord(char) for char in caption), width=3)
    draw.rounded_rectangle((82, 42, 402, 78), radius=16, fill=accent, outline=INK, width=2)
    draw.text((103, 45), "ViVi thuộc dự án P-053.", font=hand_font(19), fill=INK)
    caption_font = hand_font(30)
    lines = wrap_by_width(draw, caption, caption_font, 1600)
    if len(lines) > 2:
        caption_font = hand_font(27)
        lines = wrap_by_width(draw, caption, caption_font, 1600)
    line_height = int(caption_font.size * 1.08)
    first_y = 99 if len(lines) == 1 else 82
    for index, line in enumerate(lines[:2]):
        draw.text((94, first_y + index * line_height), line, font=caption_font, fill=INK)
    doodle_line(draw, (96, 171), (1708, 171), accent, 5, seed=len(caption) * 53, amplitude=1.8)
    canvas.save(path)


def create_intro_card(card: Card, path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), CREAM)
    add_paper_texture(canvas, 53)
    draw = ImageDraw.Draw(canvas)
    doodle_blob(canvas, (1590, 330), (360, 310), CYAN, 101)
    doodle_blob(canvas, (1720, 880), (270, 250), LILAC, 102)
    doodle_box(canvas, (74, 62, 690, 126), 26, YELLOW, seed=103, width=3, shadow=False)
    draw.text((106, 73), "Đây là dự án P-053 của AI20K Build Phase.", font=hand_font(27), fill=INK)
    title_font = hand_font(92)
    title_lines = wrap_by_width(draw, card.title, title_font, 1110)
    y = 190
    for line in title_lines:
        draw.text((92, y), line, font=title_font, fill=INK)
        y += 101
    doodle_line(draw, (94, y + 38), (1088, y + 38), BLUE, 9, seed=104, amplitude=4.0)
    body_top = y + 82
    doodle_box(canvas, (82, body_top, 1138, body_top + 190), 30, (255, 253, 247, 228), seed=105, width=3)
    body_font = font(36)
    body_y = body_top + 36
    for line in wrap_by_width(draw, card.body, body_font, 982):
        draw.text((122, body_y), line, font=body_font, fill=MUTED)
        body_y += 48
    doodle_box(canvas, (82, 928, 830, 1008), 28, MINT, seed=106, width=3, shadow=False)
    draw.text((116, 945), "Nhóm Du lịch Hà Nội thực hiện video này.", font=hand_font(31), fill=INK)
    paste_contained(
        canvas,
        ROOT / "frontend/src/media/local/common/vivi-portrait-cutout.webp",
        (1260, 160, 1880, 980),
    )
    canvas.save(path)


def create_problem_card(card: Card, path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), CREAM)
    add_paper_texture(canvas, 153)
    draw = ImageDraw.Draw(canvas)
    draw.text((84, 60), "ViVi là sản phẩm của dự án P-053.", font=hand_font(31), fill=BLUE)
    doodle_box(canvas, (70, 132, 1848, 920), 36, (255, 254, 249, 245), seed=154, width=5)
    draw.rounded_rectangle((70, 132, 112, 920), radius=17, fill=PEACH, outline=INK, width=3)
    title_font = hand_font(72)
    title_lines = wrap_by_width(draw, card.title, title_font, 1550)
    y = 210
    for line in title_lines:
        draw.text((164, y), line, font=title_font, fill=INK)
        y += 79
    doodle_line(draw, (164, y + 38), (1030, y + 38), YELLOW, 10, seed=155, amplitude=4.0)
    body_top = y + 82
    doodle_box(canvas, (150, body_top, 1760, body_top + 150), 28, MINT, seed=156, width=3, shadow=False)
    body_font = font(34)
    body_y = body_top + 31
    for line in wrap_by_width(draw, card.body, body_font, 1510):
        draw.text((192, body_y), line, font=body_font, fill=MUTED)
        body_y += 45
    footer_top = body_top + 190
    doodle_box(canvas, (150, footer_top, 1570, footer_top + 104), 26, LILAC, seed=157, width=3, shadow=False)
    draw.text(
        (190, footer_top + 25),
        "Sản phẩm đặt lịch phải làm cho lời xác nhận trở nên đáng tin cậy.",
        font=hand_font(35),
        fill=INK,
    )
    canvas.save(path)


def create_care_card(card: Card, path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), CREAM)
    add_paper_texture(canvas, 253)
    draw = ImageDraw.Draw(canvas)
    doodle_box(canvas, (76, 58, 666, 126), 28, CYAN, seed=254, width=3, shadow=False)
    draw.text((110, 71), "ViVi bắt đầu chăm sóc sau đặt lịch.", font=hand_font(29), fill=INK)
    doodle_box(canvas, (70, 158, 1320, 910), 38, LILAC, seed=255, width=5)
    title_font = hand_font(78)
    y = 242
    for line in wrap_by_width(draw, card.title, title_font, 1110):
        draw.text((122, y), line, font=title_font, fill=INK)
        y += 88
    doodle_line(draw, (126, y + 36), (1100, y + 36), BLUE, 9, seed=256, amplitude=4.5)
    body_font = font(35)
    y += 84
    for line in wrap_by_width(draw, card.body, body_font, 1080):
        draw.text((128, y), line, font=body_font, fill=MUTED)
        y += 47
    doodle_blob(canvas, (1590, 530), (280, 330), MINT, 257)
    paste_contained(
        canvas,
        ROOT / "frontend/src/media/local/common/vivi-avatar.webp",
        (1370, 270, 1815, 825),
    )
    note_font = hand_font(27)
    note_y = 850
    for line in wrap_by_width(draw, "ViVi chỉ trả lời từ nguồn đã được kiểm duyệt.", note_font, 430):
        draw.text((1380, note_y), line, font=note_font, fill=INK)
        note_y += 34
    canvas.save(path)


def create_outro_card(card: Card, path: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), CREAM)
    add_paper_texture(canvas, 353)
    draw = ImageDraw.Draw(canvas)
    draw.text((84, 54), "Nhóm Du lịch Hà Nội phát triển dự án P-053.", font=hand_font(30), fill=BLUE)
    title_font = hand_font(69)
    y = 120
    for line in wrap_by_width(draw, card.title, title_font, 1510):
        draw.text((84, y), line, font=title_font, fill=INK)
        y += 76
    doodle_line(draw, (88, y + 34), (1430, y + 34), BLUE, 9, seed=354, amplitude=4.0)
    y += 70
    body_font = font(33)
    for line in wrap_by_width(draw, card.body, body_font, 1570):
        draw.text((88, y), line, font=body_font, fill=MUTED)
        y += 45

    statements = [
        ("Khách nhận mã lịch ngay sau khi xác thực.", CYAN),
        ("Hai hồ sơ giúp thông tin đi đúng người.", LILAC),
        ("Khách tự đổi hoặc hủy khi kế hoạch thay đổi.", PEACH),
        ("Showroom vận hành trên một trạng thái thống nhất.", MINT),
    ]
    card_y = 560
    card_width = 820
    card_height = 120
    for index, (statement, color) in enumerate(statements):
        col = index % 2
        row = index // 2
        x = 86 + col * 866
        y_box = card_y + row * 150
        doodle_box(canvas, (x, y_box, x + card_width, y_box + card_height), 26, color, seed=360 + index, width=3, shadow=False)
        selected_font = hand_font(31)
        while draw.textbbox((0, 0), statement, font=selected_font)[2] > card_width - 58 and selected_font.size > 25:
            selected_font = hand_font(selected_font.size - 1)
        draw.text((x + 28, y_box + 37), statement, font=selected_font, fill=INK)

    doodle_box(canvas, (86, 920, 1270, 1008), 32, YELLOW, seed=365, width=4, shadow=False)
    draw.text((122, 938), "Bạn có thể trải nghiệm sản phẩm tại vinfast-mvp.pages.dev.", font=hand_font(31), fill=INK)
    paste_contained(canvas, ROOT / "frontend/src/media/local/common/vinfast-logo.webp", (1640, 50, 1835, 215))
    canvas.save(path)


def create_graphics() -> dict[str, Path]:
    GRAPHICS_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for item in TIMELINE:
        if isinstance(item, Clip):
            path = GRAPHICS_DIR / f"caption_{item.name}.png"
            create_caption_overlay(path, item.caption, item.accent)
        else:
            path = GRAPHICS_DIR / f"card_{item.name}.png"
            if item.style == "intro":
                create_intro_card(item, path)
            elif item.style == "problem":
                create_problem_card(item, path)
            elif item.style == "care":
                create_care_card(item, path)
            else:
                create_outro_card(item, path)
        paths[item.name] = path
    return paths


def render_card(card: Card, graphic: Path, output: Path) -> None:
    fade_out = max(0.0, card.duration - 0.3)
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-i",
            str(graphic),
            "-vf",
            f"scale={WIDTH}:{HEIGHT},fade=t=in:st=0:d=0.3,fade=t=out:st={fade_out:.3f}:d=0.3,format=yuv420p",
            "-t",
            f"{card.duration:.3f}",
            "-r",
            str(FPS),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def render_clip(clip: Clip, graphic: Path, output: Path) -> None:
    video_filter = (
        f"[0:v]setpts=(PTS-STARTPTS)/{clip.speed:.6f},"
        f"scale=-2:{HEIGHT},pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0xF7F3E8,"
        f"fps={FPS},format=rgba[base];"
        f"[1:v]format=rgba[caption];"
        "[base][caption]overlay=0:0:format=auto,format=yuv420p[outv]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{clip.start:.3f}",
            "-to",
            f"{clip.end:.3f}",
            "-i",
            str(SOURCE),
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-i",
            str(graphic),
            "-filter_complex",
            video_filter,
            "-map",
            "[outv]",
            "-t",
            f"{clip.duration:.3f}",
            "-r",
            str(FPS),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def render_segments(graphics: dict[str, Path]) -> list[Path]:
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for index, item in enumerate(TIMELINE, start=1):
        output = SEGMENTS_DIR / f"{index:02d}_{item.name}.mp4"
        if isinstance(item, Card):
            render_card(item, graphics[item.name], output)
        else:
            render_clip(item, graphics[item.name], output)
        rendered.append(output)
    return rendered


def concatenate(rendered: list[Path]) -> Path:
    concat_file = BUILD_DIR / "concat.txt"
    concat_file.write_text("".join(f"file '{path.as_posix()}'\n" for path in rendered), encoding="utf-8")
    silent = BUILD_DIR / "demo_silent.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(silent),
        ]
    )
    return silent


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(result.stdout.strip())


def add_tone(buffer: np.ndarray, start: int, tone: np.ndarray, left_gain: float, right_gain: float) -> None:
    end = min(buffer.shape[1], start + tone.size)
    if end <= start:
        return
    usable = tone[: end - start]
    buffer[0, start:end] += usable * left_gain
    buffer[1, start:end] += usable * right_gain


def synthesize_music(duration: float, output: Path) -> None:
    sample_rate = 44_100
    total_samples = int(math.ceil(duration * sample_rate))
    stereo = np.zeros((2, total_samples), dtype=np.float32)
    rng = np.random.default_rng(2053)
    bpm = 124.0
    beat_seconds = 60.0 / bpm
    bar_seconds = beat_seconds * 4.0
    chords = [
        (174.61, 220.00, 261.63),
        (220.00, 261.63, 329.63),
        (130.81, 164.81, 196.00),
        (196.00, 246.94, 293.66),
    ]

    def energy_at(seconds: float) -> float:
        if seconds < 13.5:
            return 0.56
        if seconds < 108.0:
            return 1.0
        if seconds < 114.0:
            return 0.52
        if seconds < 150.0:
            return 0.86
        return 1.08

    bar_count = int(math.ceil(duration / bar_seconds))
    for bar_index in range(bar_count):
        bar_start_seconds = bar_index * bar_seconds
        bar_start = int(bar_start_seconds * sample_rate)
        bar_length = min(int(bar_seconds * sample_rate), total_samples - bar_start)
        if bar_length <= 0:
            break
        t = np.arange(bar_length, dtype=np.float32) / sample_rate
        energy = energy_at(bar_start_seconds)
        attack = np.clip(t / 0.12, 0.0, 1.0)
        release = np.clip((bar_seconds - t) / 0.22, 0.0, 1.0)
        envelope = np.minimum(attack, release)
        chord = chords[bar_index % len(chords)]
        pad = np.zeros(bar_length, dtype=np.float32)
        for note_index, frequency in enumerate(chord):
            pad += np.sin(2.0 * np.pi * frequency * t + note_index * 0.7)
            phase = np.mod(frequency * t + note_index * 0.19, 1.0)
            pad += (phase * 2.0 - 1.0) * 0.14
        beat_phase = np.mod(t, beat_seconds)
        sidechain = 0.44 + 0.56 * (1.0 - np.exp(-beat_phase * 11.0))
        pad *= envelope * sidechain * 0.024 * energy
        add_tone(stereo, bar_start, pad, 0.90, 1.0)

        for beat in range(4):
            beat_start = bar_start + int(beat * beat_seconds * sample_rate)
            kick_length = int(0.28 * sample_rate)
            kt = np.arange(kick_length, dtype=np.float32) / sample_rate
            kick_frequency = 104.0 * np.exp(-kt * 17.0) + 43.0
            kick_phase = 2.0 * np.pi * np.cumsum(kick_frequency) / sample_rate
            kick = np.sin(kick_phase) * np.exp(-kt * 15.0) * 0.29 * energy
            if bar_start_seconds < 13.5 and beat % 2 == 1:
                kick *= 0.0
            add_tone(stereo, beat_start, kick, 1.0, 1.0)

            if beat in (1, 3) and bar_start_seconds >= 13.5:
                snare_length = int(0.20 * sample_rate)
                st = np.arange(snare_length, dtype=np.float32) / sample_rate
                snare = rng.standard_normal(snare_length).astype(np.float32)
                snare = np.concatenate((np.zeros(1, dtype=np.float32), np.diff(snare)))
                clap = np.sin(2.0 * np.pi * 182.0 * st) * np.exp(-st * 24.0)
                snare = (snare * 0.026 + clap * 0.045) * np.exp(-st * 13.0) * energy
                for offset in (0, int(0.018 * sample_rate), int(0.034 * sample_rate)):
                    add_tone(stereo, beat_start + offset, snare, 0.88, 1.0)

            bass_frequency = chord[0] * 0.5
            bass_length = int(0.40 * sample_rate)
            bt = np.arange(bass_length, dtype=np.float32) / sample_rate
            bass = (
                np.sin(2.0 * np.pi * bass_frequency * bt)
                + 0.24 * np.sin(2.0 * np.pi * bass_frequency * 2.0 * bt)
            )
            bass *= np.exp(-bt * 5.4) * 0.105 * energy
            if bar_start_seconds < 13.5 and beat not in (0, 2):
                bass *= 0.0
            add_tone(stereo, beat_start, bass, 1.0, 1.0)

        for eighth in range(8):
            step_seconds = eighth * beat_seconds * 0.5
            step_start = bar_start + int(step_seconds * sample_rate)
            note_frequency = chord[(eighth + bar_index) % 3] * (2.0 if eighth % 2 == 0 else 4.0)
            pluck_length = int(0.30 * sample_rate)
            pt = np.arange(pluck_length, dtype=np.float32) / sample_rate
            pluck = (
                np.sin(2.0 * np.pi * note_frequency * pt)
                + 0.28 * np.sin(2.0 * np.pi * note_frequency * 2.0 * pt)
                + 0.10 * np.sin(2.0 * np.pi * note_frequency * 3.0 * pt)
            )
            pluck *= np.exp(-pt * 11.5) * 0.046 * energy
            if bar_start_seconds < 6.5:
                pluck *= 0.45
            pan_left = 0.95 if eighth % 2 == 0 else 0.48
            pan_right = 0.48 if eighth % 2 == 0 else 0.95
            add_tone(stereo, step_start, pluck, pan_left, pan_right)

            hat_start = step_start
            hat_length = int((0.105 if eighth in (3, 7) else 0.052) * sample_rate)
            ht = np.arange(hat_length, dtype=np.float32) / sample_rate
            hat = rng.standard_normal(hat_length).astype(np.float32)
            hat = np.concatenate((np.zeros(1, dtype=np.float32), np.diff(hat)))
            hat *= np.exp(-ht * (34.0 if eighth in (3, 7) else 68.0))
            hat *= (0.014 if eighth % 2 else 0.009) * energy
            if bar_start_seconds < 13.5:
                hat *= 0.28
            add_tone(stereo, hat_start, hat, 0.62, 0.88)

        if bar_index % 2 == 1 and bar_start_seconds >= 13.5:
            melody_steps = (0.0, 1.5, 2.5, 3.25)
            melody_notes = (chord[2] * 2.0, chord[1] * 2.0, chord[2] * 2.0, chord[0] * 4.0)
            for step, note_frequency in zip(melody_steps, melody_notes):
                melody_start = bar_start + int(step * beat_seconds * sample_rate)
                melody_length = int(0.52 * sample_rate)
                mt = np.arange(melody_length, dtype=np.float32) / sample_rate
                melody = (
                    np.sin(2.0 * np.pi * note_frequency * mt)
                    + 0.18 * np.sin(2.0 * np.pi * note_frequency * 2.0 * mt)
                )
                melody *= np.exp(-mt * 5.8) * 0.038 * energy
                add_tone(stereo, melody_start, melody, 0.72, 1.0)

    for transition in (13.5, 108.0, 114.0, 150.0, max(0.0, duration - 10.5)):
        start_seconds = max(0.0, transition - 0.75)
        start = int(start_seconds * sample_rate)
        length = min(int(0.75 * sample_rate), total_samples - start)
        if length <= 0:
            continue
        rt = np.arange(length, dtype=np.float32) / sample_rate
        noise = rng.standard_normal(length).astype(np.float32)
        noise = np.concatenate((np.zeros(1, dtype=np.float32), np.diff(noise)))
        rise = noise * np.square(rt / 0.75) * 0.016
        shimmer_frequency = 620.0 + 980.0 * np.square(rt / 0.75)
        shimmer_phase = 2.0 * np.pi * np.cumsum(shimmer_frequency) / sample_rate
        rise += np.sin(shimmer_phase) * np.square(rt / 0.75) * 0.020
        add_tone(stereo, start, rise, 0.75, 1.0)

    fade_samples = min(int(1.2 * sample_rate), total_samples // 2)
    fade = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    stereo[:, :fade_samples] *= fade
    stereo[:, -fade_samples:] *= fade[::-1]
    peak = float(np.max(np.abs(stereo))) or 1.0
    stereo *= 0.86 / peak
    pcm = np.clip(stereo.T * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())


def mux_audio(silent: Path, duration: float) -> None:
    music = BUILD_DIR / "original_music.wav"
    synthesize_music(duration, music)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(silent),
            "-i",
            str(music),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ]
    )


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Source screen recording is missing: {SOURCE}")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("FFmpeg and FFprobe are required.")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    graphics = create_graphics()
    rendered = render_segments(graphics)
    silent = concatenate(rendered)
    duration = probe_duration(silent)
    if duration >= 180.0:
        raise SystemExit(f"The assembled video is too long: {duration:.3f} seconds")
    mux_audio(silent, duration)
    final_duration = probe_duration(OUTPUT)
    print(f"Created {OUTPUT} ({final_duration:.3f} seconds)")


if __name__ == "__main__":
    main()
