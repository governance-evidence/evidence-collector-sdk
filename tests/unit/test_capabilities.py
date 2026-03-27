from collector.capabilities import StreamCapabilities, capabilities_from_config
from collector.config import fraud_detection_config
from collector.core.signal import SignalType
from collector.output.decision_event_writer import SCHEMA_VERSION


class TestStreamCapabilities:
    def test_create(self):
        cap = StreamCapabilities(
            supported_signal_types=frozenset({SignalType.EVENT}),
            schema_version="0.1.0",
            max_batch_size=500,
        )
        assert SignalType.EVENT in cap.supported_signal_types
        assert cap.max_batch_size == 500
        assert cap.sdk_version == "0.1.0"


class TestCapabilitiesFromConfig:
    def test_fraud_config(self):
        cfg = fraud_detection_config()
        cap = capabilities_from_config(cfg)
        assert cap.supported_signal_types == cfg.enabled_signal_types
        assert cap.schema_version == SCHEMA_VERSION
        assert cap.max_batch_size == 1000

    def test_custom_batch_size(self):
        cfg = fraud_detection_config()
        cap = capabilities_from_config(cfg, max_batch_size=200)
        assert cap.max_batch_size == 200
