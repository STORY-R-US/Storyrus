import hashlib
from types import SimpleNamespace

import pytest

from app import storage
from app.workers.handlers.editorial_book import Pipeline, signature


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("stage", ["cover:expand", "cover:text", "reading"])
async def test_provenance_does_not_repurchase_saved_stages(monkeypatch, legacy, stage):
    pipe = object.__new__(Pipeline)
    pipe.designed = False
    pipe.base = {"photos": ["same-photo"]}
    pipe.project = SimpleNamespace(id="project")
    revision = {"id": "same-request", "art_revision": "same-request", "adjustment": "same-edit"}
    inputs = {"source_sha256": "same-pixels", "transform": {"scale": 0.63}}
    cached_revision = {**revision, "source_asset_id": "saved-original"} if legacy else revision
    key = f"editorial/project/{signature([pipe.base, stage, {**inputs, 'requested_revision': cached_revision}])}.png"
    data = b"already-purchased-result"
    cached = SimpleNamespace(meta={"sha256": hashlib.sha256(data).hexdigest()})
    pipe.revision_for = lambda _: {**revision, "source_asset_id": "saved-original"}
    pipe.cached = lambda candidate: cached if candidate == key else None
    pipe.record = lambda *args, **kwargs: None
    monkeypatch.setattr(
        storage,
        "get_bytes",
        lambda candidate: data if candidate == key else pytest.fail("Wrong cached asset"),
    )

    async def forbidden(_):
        pytest.fail("A saved result must never invoke the provider again")

    result, _ = await pipe.stage(stage, inputs, forbidden)
    assert result == data


def test_editorial_snapshot_is_platform_independent_and_accepts_legacy_windows_order():
    from app.services import editorial_profile

    current = editorial_profile.snapshot("2026-11-05.3")
    assert current["sha256"] == "59599394322c9d74f47af29a8295f06fa4d09f890a77aad0780f99c53de0a075"
    legacy = editorial_profile.snapshot("2026-11-05.3", legacy_windows_order=True)
    assert legacy["sha256"] != current["sha256"]
    assert editorial_profile.policy({"editorial": current}) == editorial_profile.policy(
        {"editorial": legacy}
    )
    with pytest.raises(ValueError, match="Perfil editorial alterado"):
        editorial_profile.policy({"editorial": {**current, "sha256": "modified"}})
