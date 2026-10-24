"""Tests for the SCORE bands visualization."""

import re

import numpy as np
import polars as pl

from desdeo.tools.score_bands import CustomClusterOptions, SCOREBandsConfig, plot_score, score_json

RGBA = re.compile(r"rgba\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\s*\)")


def test_band_colors_are_on_the_0_to_255_scale():
    """Plotly reads the red, green and blue of an rgba() color from 0 to 255, so fractions draw the bands black."""
    data = pl.DataFrame(np.random.default_rng(0).uniform(size=(60, 3)), schema=["f1", "f2", "f3"], orient="row")
    clusters = [1] * 20 + [2] * 20 + [3] * 20
    result = score_json(data, SCOREBandsConfig(clustering_algorithm=CustomClusterOptions(clusters=clusters)))

    figure = plot_score(data, result)

    channels = [tuple(float(v) for v in RGBA.fullmatch(t.fillcolor).groups()[:3]) for t in figure.data if t.fillcolor]
    assert len(set(channels)) == len(set(clusters))
    assert all(value == int(value) and 0 <= value <= 255 for rgb in channels for value in rgb)
    assert all(max(rgb) > 1 for rgb in channels)
