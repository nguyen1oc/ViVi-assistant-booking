import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publish_site_media.py"
SPEC = importlib.util.spec_from_file_location("publish_site_media", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
PUBLISH_SITE_MEDIA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLISH_SITE_MEDIA)


@pytest.mark.parametrize("destination_kind", ["same", "child", "parent"])
def test_publish_rejects_overlapping_media_trees(tmp_path, destination_kind):
    source = tmp_path / "source"
    source.mkdir()
    destinations = {
        "same": source,
        "child": source / "published",
        "parent": tmp_path,
    }

    with pytest.raises(ValueError, match="must not overlap"):
        PUBLISH_SITE_MEDIA._assert_separate_media_trees(source, destinations[destination_kind])


def test_publish_accepts_separate_media_trees(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "published"

    PUBLISH_SITE_MEDIA._assert_separate_media_trees(source, destination)
