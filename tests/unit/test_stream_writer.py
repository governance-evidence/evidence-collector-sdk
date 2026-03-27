import json

import pytest

from collector.output.stream_writer import JsonlStreamWriter, StreamWriter


class TestStreamWriterProtocol:
    def test_jsonl_satisfies_protocol(self):
        assert issubclass(JsonlStreamWriter, StreamWriter)


class TestJsonlStreamWriter:
    def test_write_and_read(self, tmp_path):
        path = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(path)
        events = [{"decision_id": "d1", "score": 0.9}, {"decision_id": "d2", "score": 0.5}]
        writer.write_batch(events)
        writer.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]
        assert parsed[0]["decision_id"] == "d1"
        assert parsed[1]["score"] == 0.5

    def test_append_mode(self, tmp_path):
        path = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(path)
        writer.write_batch([{"id": 1}])
        writer.write_batch([{"id": 2}])
        writer.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_empty_batch(self, tmp_path):
        path = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(path)
        writer.write_batch([])
        writer.close()
        assert path.read_text() == ""

    def test_context_manager_closes_writer(self, tmp_path):
        path = tmp_path / "output.jsonl"

        with JsonlStreamWriter(path) as writer:
            writer.write_batch([{"decision_id": "d1"}])
            assert writer.closed is False

        assert writer.closed is True
        assert path.read_text().strip() == '{"decision_id": "d1"}'

    def test_context_manager_closes_on_exception(self, tmp_path):
        path = tmp_path / "output.jsonl"

        try:
            with JsonlStreamWriter(path) as writer:
                writer.write_batch([{"decision_id": "d1"}])
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        assert writer.closed is True

    def test_close_is_idempotent(self, tmp_path):
        path = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(path)

        writer.close()
        writer.close()

        assert writer.closed is True

    def test_write_after_close_raises(self, tmp_path):
        path = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(path)
        writer.close()

        with pytest.raises(RuntimeError, match="closed stream writer"):
            writer.write_batch([{"decision_id": "d1"}])

    def test_non_serializable_value_raises(self, tmp_path):
        path = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(path)

        with pytest.raises(TypeError):
            writer.write_batch([{"bad": object()}])

        writer.close()
