from meridian_expert.investigation.bundle_registry import BundleRegistry


def test_registry_loads():
    reg = BundleRegistry()
    assert any(b["name"] == "meridian_model_core" for b in reg.list())
    ranked = reg.rank_for("theory", "model")
    assert ranked
