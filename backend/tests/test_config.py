import os
from pathlib import Path
import re
import warnings
import pytest
from dotenv import dotenv_values

from app.config import settings, Settings


def test_env_parsing_generates_zero_warnings():
    """Verify that python-dotenv loads the configuration without any parse warnings."""
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        # Find active .env file
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            env_path = Path.cwd() / "agentmemory-ai" / ".env"
        if not env_path.exists():
            env_path = Path(__file__).resolve().parent.parent.parent / ".env"

        assert env_path.exists(), f".env not found at {env_path}"
        values = dotenv_values(env_path)
        assert len(values) > 0, "Parsed .env is empty"

        # Assert no syntax warnings were raised
        parse_warnings = [
            w for w in captured_warnings
            if "could not parse statement" in str(w.message).lower()
        ]
        assert len(parse_warnings) == 0, f"Expected 0 dotenv parse warnings, got {parse_warnings}"


def test_env_syntax_strict_key_value():
    """Verify that every line in .env strictly adheres to valid KEY=VALUE syntax."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_path = Path.cwd() / "agentmemory-ai" / ".env"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"

    assert env_path.exists()
    line_pattern = re.compile(r"^[A-Z][A-Z0-9_]*=.*$")

    with open(env_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            stripped = line.strip()
            # Comments and blank lines are allowed
            if not stripped or stripped.startswith("#"):
                continue

            # Must match KEY=VALUE
            assert line_pattern.match(stripped), (
                f"Line {line_num} violates KEY=VALUE syntax: {stripped[:15]}..."
            )
            # Ensure no colon delimiters in place of equals
            assert ":" not in stripped.split("=", 1)[0], (
                f"Line {line_num} contains colon in variable name: {stripped[:15]}..."
            )


def test_required_variables_status_present():
    """Verify that all required environment variables are loaded and present."""
    status_report = settings.get_status_report()

    expected_keys = [
        "LYZR_API_KEY",
        "LYZR_API_URL",
        "LYZR_RESEARCH_AGENT_ID",
        "LYZR_USER_ID",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "QDRANT_COLLECTION_NAME",
        "OMI_API_KEY",
    ]

    for key in expected_keys:
        assert key in status_report, f"Variable {key} missing from status report"
        assert status_report[key] == "PRESENT", f"Variable {key} is {status_report[key]}"


def test_env_example_contains_only_placeholders():
    """Verify that .env.example contains only non-secret placeholders."""
    example_path = Path.cwd() / ".env.example"
    if not example_path.exists():
        example_path = Path.cwd() / "agentmemory-ai" / ".env.example"
    if not example_path.exists():
        example_path = Path(__file__).resolve().parent.parent.parent / ".env.example"

    assert example_path.exists()
    values = dotenv_values(example_path)

    # Check that secrets are placeholders
    assert "your_lyzr_api_key_here" in values.get("LYZR_API_KEY", "")
    assert "your_qdrant_api_key_here" in values.get("QDRANT_API_KEY", "")
    assert "your_omi_api_key_here" in values.get("OMI_API_KEY", "")


def test_gitignore_excludes_env():
    """Verify that .gitignore excludes .env files."""
    gitignore_path = Path.cwd() / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path = Path.cwd() / "agentmemory-ai" / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path = Path.cwd().parent / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path = Path(__file__).resolve().parent.parent.parent / ".gitignore"

    assert gitignore_path.exists()
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".env" in content
    assert ".env.*" in content
    assert "!.env.example" in content
