from datetime import UTC, datetime

import pytest

from collector.core.provenance import ProvenanceChain, ProvenanceStep, content_hash


class TestProvenanceStep:
    def _make(self, **overrides):
        defaults = {
            "step_name": "transform",
            "input_hash": "aaa",
            "output_hash": "bbb",
            "transform_name": "test_transform",
            "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        }
        return ProvenanceStep(**(defaults | overrides))

    def test_create(self):
        s = self._make()
        assert s.step_name == "transform"
        assert s.input_hash == "aaa"

    def test_empty_step_name(self):
        with pytest.raises(ValueError, match="step_name"):
            self._make(step_name="")

    def test_empty_transform_name(self):
        with pytest.raises(ValueError, match="transform_name"):
            self._make(transform_name="")


class TestProvenanceChain:
    def test_create(self):
        c = ProvenanceChain(origin="src")
        assert c.origin == "src"
        assert c.steps == ()
        assert c.integrity_verified is False

    def test_empty_origin(self):
        with pytest.raises(ValueError, match="origin"):
            ProvenanceChain(origin="")

    def test_append(self):
        c = ProvenanceChain(origin="src")
        step = ProvenanceStep(
            step_name="s1",
            input_hash="a",
            output_hash="b",
            transform_name="t1",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        c2 = c.append(step)
        assert len(c2.steps) == 1
        assert c2.integrity_verified is False
        # original unchanged
        assert len(c.steps) == 0

    def test_verify_empty(self):
        c = ProvenanceChain(origin="src").verify()
        assert c.integrity_verified is True

    def test_verify_valid_chain(self):
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        s1 = ProvenanceStep("s1", "a", "b", "t1", ts)
        s2 = ProvenanceStep("s2", "b", "c", "t2", ts)
        c = ProvenanceChain(origin="src", steps=(s1, s2)).verify()
        assert c.integrity_verified is True

    def test_verify_broken_chain(self):
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        s1 = ProvenanceStep("s1", "a", "b", "t1", ts)
        s2 = ProvenanceStep("s2", "WRONG", "c", "t2", ts)
        with pytest.raises(ValueError, match="Broken hash chain"):
            ProvenanceChain(origin="src", steps=(s1, s2)).verify()


class TestContentHash:
    def test_deterministic(self):
        h1 = content_hash({"a": 1, "b": 2})
        h2 = content_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_different_data(self):
        h1 = content_hash({"a": 1})
        h2 = content_hash({"a": 2})
        assert h1 != h2
