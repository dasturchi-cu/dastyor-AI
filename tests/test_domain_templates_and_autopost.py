"""Tests for domain-specific CV templates."""
from __future__ import annotations

from pathlib import Path


def test_cv_template_contains_domain_css_classes():
    tmpl_path = Path("templates/cv_template.html")
    assert tmpl_path.exists()
    content = tmpl_path.read_text(encoding="utf-8")
    assert ".tpl-it" in content
    assert ".tpl-finance" in content
    assert ".tpl-medical" in content
    assert ".tpl-marketing" in content


def test_webapp_cv_contains_domain_template_cards():
    cv_path = Path("webapp/cv.html")
    assert cv_path.exists()
    content = cv_path.read_text(encoding="utf-8")
    assert 'id="tpl-it"' in content
    assert 'id="tpl-finance"' in content
    assert 'id="tpl-medical"' in content
    assert 'id="tpl-marketing"' in content
