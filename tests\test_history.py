from storage.history import HistoryStore


def test_history_diff_tracks_new_and_status(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    store.save("2026-10-16", {"cards": [{"task_id": "VT-1", "status": "Ready for QA", "description": "a"}]})
    delta = store.diff({"cards": [{"task_id": "VT-1", "status": "Verifying", "description": "b"},
                                  {"task_id": "VT-2", "status": "Ready for QA", "description": "c"}]})
    assert delta["new"] == ["VT-2"]
    assert delta["status_changed"] == ["VT-1"]
    assert delta["description_changed"] == ["VT-1"]
