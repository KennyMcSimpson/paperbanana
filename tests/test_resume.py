"""Resume checkpoints must come from completed refinement iterations."""

from __future__ import annotations

import json

import pytest

from paperbanana.core.resume import load_resume_state


@pytest.fixture
def run_dir(tmp_path):
    run_dir = tmp_path / "run_test"
    run_dir.mkdir()
    (run_dir / "run_input.json").write_text(
        json.dumps(
            {
                "source_context": "Test methodology",
                "communicative_intent": "Test caption",
                "diagram_type": "methodology",
            }
        ),
        encoding="utf-8",
    )
    return run_dir


def _complete_iteration(run_dir, iteration):
    directory = run_dir / f"iter_{iteration}"
    directory.mkdir()
    (directory / "details.json").write_text(
        json.dumps(
            {
                "description": f"Description {iteration}",
                "critique": {"revised_description": f"Revision {iteration}"},
            }
        ),
        encoding="utf-8",
    )
    image = run_dir / f"diagram_iter_{iteration}.png"
    image.write_bytes(b"image")
    return image


@pytest.mark.parametrize("failure_note", [True, False], ids=["failed", "empty"])
def test_resume_skips_incomplete_later_iteration(run_dir, failure_note):
    image = _complete_iteration(run_dir, 1)
    later = run_dir / "iter_2"
    later.mkdir()
    if failure_note:
        (later / "failure.json").write_text('{"failed": true}', encoding="utf-8")

    state = load_resume_state(str(run_dir.parent), run_dir.name)

    assert state.last_iteration == 1
    assert state.last_description == "Revision 1"
    assert state.last_image_path == str(image)


def test_resume_skips_multiple_failed_iterations(run_dir):
    image = _complete_iteration(run_dir, 1)
    for iteration in (2, 10):
        directory = run_dir / f"iter_{iteration}"
        directory.mkdir()
        (directory / "failure.json").write_text('{"failed": true}', encoding="utf-8")

    state = load_resume_state(str(run_dir.parent), run_dir.name)

    assert state.last_iteration == 1
    assert state.last_image_path == str(image)


def test_resume_selects_latest_completed_iteration_numerically(run_dir):
    _complete_iteration(run_dir, 2)
    image = _complete_iteration(run_dir, 10)

    state = load_resume_state(str(run_dir.parent), run_dir.name)

    assert state.last_iteration == 10
    assert state.last_description == "Revision 10"
    assert state.last_image_path == str(image)


@pytest.mark.parametrize("failure_note", [True, False], ids=["failed", "empty"])
def test_resume_uses_planning_when_no_iteration_completed(run_dir, failure_note):
    directory = run_dir / "iter_1"
    directory.mkdir()
    if failure_note:
        (directory / "failure.json").write_text('{"failed": true}', encoding="utf-8")
    (run_dir / "planning.json").write_text(
        json.dumps({"optimized_description": "Planning description"}), encoding="utf-8"
    )

    state = load_resume_state(str(run_dir.parent), run_dir.name)

    assert state.last_iteration == 0
    assert state.last_description == "Planning description"
    assert state.last_image_path is None


def test_resume_without_completed_iteration_or_planning_raises(run_dir):
    (run_dir / "iter_1").mkdir()

    with pytest.raises(ValueError, match="No iterations or planning.json"):
        load_resume_state(str(run_dir.parent), run_dir.name)
