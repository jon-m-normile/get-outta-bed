import shutil
import subprocess

import pytest

from getouttabed import audio, paths


def test_probe_bundled_wav():
    assert audio.probe_duration(paths.BUNDLED_ALARM_SOUND) > 0


def test_probe_rejects_non_audio(tmp_path):
    f = tmp_path / "notes.mp3"
    f.write_text("not really audio")
    assert audio.probe_duration(f) is None


@pytest.mark.skipif(not shutil.which("gst-launch-1.0"), reason="gst-launch-1.0 not installed")
def test_probe_m4a(tmp_path):
    f = tmp_path / "memo.m4a"
    r = subprocess.run(["gst-launch-1.0", "-q", "audiotestsrc", "num-buffers=130", "!", "audioconvert", "!",
                        "avenc_aac", "!", "mp4mux", "!", "filesink", f"location={f}"], capture_output=True)
    if r.returncode != 0:
        pytest.skip("AAC encoder (gstreamer1.0-libav) not available")
    assert 2.5 < audio.probe_duration(f) < 3.5
