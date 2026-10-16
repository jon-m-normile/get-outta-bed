import json

from getouttabed import model


def test_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    s = model.Settings()
    s.recordings.append(model.Recording(id="r1", name="Mom", filename="r1.m4a", duration=4.2))
    s.alarms.append(model.Alarm(hour=6, minute=45, label="School", rrule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
                                start_date="2026-10-19", recordings=["r1"], shuffle=True, puzzle="math"))
    s.last_puzzle = "simon"
    model.save(s, path)
    loaded = model.load(path)
    assert loaded == s
    assert not (tmp_path / "settings.json.tmp").exists()


def test_corrupt_file_backed_up(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    path = tmp_path / "settings.json"
    path.write_text("{not json")
    s = model.load(path)
    assert s == model.Settings()
    backups = list(tmp_path.glob("settings.json.corrupt-*"))
    assert len(backups) == 1 and backups[0].read_text() == "{not json"


def test_wrong_shape_recovers(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    path = tmp_path / "settings.json"
    path.write_text(json.dumps([1, 2, 3]))
    assert model.load(path) == model.Settings()


def test_unknown_keys_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"alarms": [{"hour": 5, "minute": 30, "future_field": 1}]}))
    s = model.load(path)
    assert s.alarms[0].hour == 5


def test_remove_recording_from_playlists():
    s = model.Settings()
    s.recordings = [model.Recording("a", "A", "a.mp3"), model.Recording("b", "B", "b.mp3")]
    s.alarms = [model.Alarm(recordings=["a", "b"])]
    s.remove_recording("a")
    assert [r.id for r in s.recordings] == ["b"] and s.alarms[0].recordings == ["b"]


def test_format_time():
    assert model.format_time(0, 5) == "00:05"
    assert model.format_time(12, 0) == "12:00"
    assert model.format_time(6, 45) == "06:45"
    assert model.format_time(18, 45) == "18:45"
