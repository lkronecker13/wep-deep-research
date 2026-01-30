"""Unit tests for evaluation dataset export functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.evaluation_dataset import export_dataset_to_json, get_evaluation_dataset


def test__export_dataset_to_json__creates_valid_file(tmp_path: Path) -> None:
    """Should create JSON file with valid dataset structure."""
    output_path = tmp_path / "test_output.json"
    result_path = export_dataset_to_json(str(output_path))

    assert output_path.exists()
    assert result_path == output_path.resolve()

    data = json.loads(output_path.read_text())
    assert "version" in data
    assert "questions" in data
    assert len(data["questions"]) == 100  # Expected dataset size
    assert data["version"] == "1.0.0"


def test__export_dataset_to_json__creates_parent_directories(tmp_path: Path) -> None:
    """Should create missing parent directories automatically."""
    output_path = tmp_path / "nested" / "dir" / "output.json"
    export_dataset_to_json(str(output_path))

    assert output_path.exists()
    assert output_path.parent.exists()


def test__export_dataset_to_json__accepts_path_object(tmp_path: Path) -> None:
    """Should accept Path objects in addition to strings."""
    output_path = tmp_path / "test.json"
    result_path = export_dataset_to_json(output_path)

    assert output_path.exists()
    assert isinstance(result_path, Path)


def test__export_dataset_to_json__rejects_path_outside_project(tmp_path: Path) -> None:
    """Should reject paths outside project directory for security."""
    outside_path = "/usr/local/malicious.json"

    with pytest.raises(ValueError, match="within project directory"):
        export_dataset_to_json(outside_path)


def test__export_dataset_to_json__rejects_path_traversal(tmp_path: Path) -> None:
    """Should prevent directory traversal attacks."""
    traversal_path = "../../etc/passwd"

    with pytest.raises(ValueError, match="within project directory"):
        export_dataset_to_json(traversal_path)


def test__export_dataset_to_json__handles_permission_error(tmp_path: Path) -> None:
    """Should raise PermissionError when directory is read-only."""
    output_dir = tmp_path / "readonly"
    output_dir.mkdir()
    output_dir.chmod(0o444)  # Read-only

    with pytest.raises(PermissionError):
        export_dataset_to_json(str(output_dir / "output.json"))


def test__export_dataset_to_json__produces_pretty_json(tmp_path: Path) -> None:
    """Should format JSON with indentation for readability."""
    output_path = tmp_path / "pretty.json"
    export_dataset_to_json(str(output_path))

    content = output_path.read_text()

    # Check for indentation (pretty-printed)
    assert "  " in content  # Should have 2-space indentation
    assert content.count("\n") > 100  # Should be multi-line


def test__get_evaluation_dataset__returns_100_questions() -> None:
    """Should return dataset with 100 questions."""
    dataset = get_evaluation_dataset()

    assert len(dataset.questions) == 100
    assert dataset.version == "1.0.0"


def test__get_evaluation_dataset__has_all_categories() -> None:
    """Should include questions from all 8 categories."""
    dataset = get_evaluation_dataset()
    categories = {q.category for q in dataset.questions}

    expected_categories = {
        "technical",
        "business",
        "scientific",
        "historical",
        "comparative",
        "emerging",
        "synthesis",
        "validation",
    }

    assert categories == expected_categories
