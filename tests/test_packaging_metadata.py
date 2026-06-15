"""The published distribution must carry discovery metadata (classifiers,
keywords). These feed PyPI search and Libraries.io. Reads the *installed*
distribution metadata, so run `pip install -e .` after changing pyproject.toml
to refresh editable metadata before this test will see new fields."""

from importlib import metadata

DIST = "capitalcom-cli"

EXPECTED_CLASSIFIERS = {
    "Environment :: Console",
    "Intended Audience :: Financial and Insurance Industry",
    "Topic :: Office/Business :: Financial :: Investment",
    "Programming Language :: Python :: 3.12",
}


def test_expected_classifiers_present() -> None:
    classifiers = set(metadata.metadata(DIST).get_all("Classifier") or [])
    missing = EXPECTED_CLASSIFIERS - classifiers
    assert not missing, f"missing classifiers: {sorted(missing)}"


def test_expected_keywords_present() -> None:
    keywords = metadata.metadata(DIST).get("Keywords", "")
    assert "capital.com" in keywords
    assert "trading" in keywords


def test_expected_project_urls_present() -> None:
    urls = metadata.metadata(DIST).get_all("Project-URL") or []
    labels = {entry.split(",", 1)[0].strip().lower() for entry in urls}
    assert {"documentation", "changelog", "source"} <= labels
