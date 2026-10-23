import numpy as np
import pytest

from recogni.recognition import RecognitionError, _scene_indices, _unit_vector, report_dict
from recogni.scenes import Scene


def test_unit_vector_normalizes_embedding():
    assert np.allclose(_unit_vector(np.array([3.0, 4.0])), [0.6, 0.8])


def test_unit_vector_rejects_empty_embedding():
    with pytest.raises(RecognitionError):
        _unit_vector(np.array([0.0, 0.0]))


def test_scene_indices_link_sample_time_to_scene():
    scenes = [Scene(0, 3), Scene(3, 7)]
    assert _scene_indices(2.5, scenes) == (1,)
    assert _scene_indices(3, scenes) == (2,)


def test_report_contains_source_time_and_review_limitations(tmp_path):
    report = report_dict(tmp_path / "movie.mp4", [])
    assert report["video"].endswith("movie.mp4")
    assert report["characters"] == []
    assert "candidates" in report["limitations"][1]
