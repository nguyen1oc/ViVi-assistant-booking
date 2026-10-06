from datetime import datetime

from src.agents import utils


# test case of Chau + kiểm tra system prompt được đọc từ file cấu hình
def test_get_system_prompt_reads_configured_file(monkeypatch, tmp_path):
    prompt_file = tmp_path / "system_prompt.md"
    prompt_file.write_text("SYSTEM PROMPT FOR TEST", encoding="utf-8")
    monkeypatch.setattr(utils, "SYSTEM_PROMPT_PATH", prompt_file)
    fixed_now = datetime(2026, 8, 8, 20, 35, 44)

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(utils, "datetime", FixedDateTime)

    assert utils.get_system_prompt() == (
        "SYSTEM PROMPT FOR TEST\n\n"
        "--- CURRENT TIME CONTEXT ---\n"
        "Today is: Thứ 7, 2026-08-08 20:35:44 (Vietnam Local Time)"
    )


# test case of Chau + kiểm tra system prompt dùng fallback khi file bị thiếu
def test_get_system_prompt_falls_back_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(utils, "SYSTEM_PROMPT_PATH", tmp_path / "missing.md")

    assert "VinFast Test Drive Virtual Assistant" in utils.get_system_prompt()
