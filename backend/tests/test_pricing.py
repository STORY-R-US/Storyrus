"""Tabela de preço: imagem OpenAI, tokens Claude e vídeo."""

from app.services import pricing


def test_image_cost_flat_without_usage():
    assert pricing.image_cost(None) == pricing.settings.price_openai_image_usd
    assert pricing.image_cost({}) == pricing.settings.price_openai_image_usd


def test_text_cost_claude_tokens():
    # 1M in + 1M out = 15 + 75
    assert pricing.text_cost({"input_tokens": 1_000_000, "output_tokens": 1_000_000}) == 90.0
    assert pricing.text_cost({}) == 0.0


def test_video_cost_per_second():
    assert pricing.video_cost(10) == 1.0
    assert pricing.video_cost(0) == 0.0
    assert pricing.video_cost(None) == 0.0


def test_add_usd_ignores_none():
    unit = pricing.settings.price_openai_image_usd
    assert pricing.add_usd(unit, None, unit) == round(unit * 2, 6)


def test_openai_image_cost_flat():
    assert pricing.openai_image_cost(None) == pricing.settings.price_openai_image_usd


def test_estimate_job_usd_video_and_avatar():
    unit = pricing.openai_image_cost(None)
    assert pricing.estimate_job_usd("VIDEO") == pricing.video_cost(5)
    # Avatar = geracao + refine tipico
    assert abs(pricing.estimate_job_usd("AVATAR") - (unit * 2.0)) < 1e-9
