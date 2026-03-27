import pytest

from collector.core.attribution import Attribution


class TestAttribution:
    def _make(self, **overrides):
        defaults = {
            "actor_id": "model-v3",
            "actor_type": "system",
        }
        return Attribution(**(defaults | overrides))

    def test_create(self):
        a = self._make()
        assert a.actor_id == "model-v3"
        assert a.actor_type == "system"
        assert a.organizational_role is None
        assert a.delegation_chain == ()
        assert a.responsibility_boundary is None

    def test_full_attribution(self):
        a = self._make(
            organizational_role="fraud-analyst",
            delegation_chain=("ceo", "cro", "fraud-team"),
            responsibility_boundary="fraud-detection-pipeline",
        )
        assert a.organizational_role == "fraud-analyst"
        assert len(a.delegation_chain) == 3

    def test_empty_actor_id(self):
        with pytest.raises(ValueError, match="actor_id"):
            self._make(actor_id="")

    def test_invalid_actor_type(self):
        with pytest.raises(ValueError, match="actor_type"):
            self._make(actor_type="robot")

    def test_valid_actor_types(self):
        for t in ("system", "human", "hybrid"):
            a = self._make(actor_type=t)
            assert a.actor_type == t
