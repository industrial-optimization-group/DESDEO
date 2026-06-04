"""Provides some visualization functions."""

from typing import Any

import plotly.graph_objects as go


def scatter_plot_comparison(
    *results: Any,
    x_key: str = "f_1",
    y_key: str = "f_2",
    z_key: str | None = None,
    reference_point: dict[str, float] | None = None,
    names: list[str] | None = None,
) -> go.Figure:
    """Plots multiple sets of data in a scatter plot (2D or 3D depending on the data).

    Parameters:
        *results: Variable number of result objects, each containing outputs with keys for x, y, and optionally z.
        x_key: Key for the x-axis data in the outputs.
        y_key: Key for the y-axis data in the outputs.
        z_key: Key for the z-axis data in the outputs (optional, for 3D plots).
        reference_point: A dictionary with keys matching x_key, y_key, and optionally z_key,
        representing the reference point to plot.
        names: List of names for each data set to display in the legend.

    Returns:
        go.Figure: Figure instance that shows the data.
    """
    traces = []
    is_3d = z_key is not None and all(z_key in result.outputs for result in results)

    if names is None:
        names = [f"Dataset {i + 1}" for i in range(len(results))]

    for i, (result, name) in enumerate(zip(results, names, strict=False)):
        color = f"hsl({i * 360 / len(results)}, 100%, 50%)"  # Generate distinct colors
        if is_3d:
            trace = go.Scatter3d(
                x=result.outputs[x_key],
                y=result.outputs[y_key],
                z=result.outputs[z_key],
                mode="markers",
                marker={"size": 4, "color": color, "symbol": "circle"},
                name=name,
            )
        else:
            trace = go.Scatter(
                x=result.outputs[x_key],
                y=result.outputs[y_key],
                mode="markers",
                marker={"size": 8, "color": color, "symbol": "circle"},
                name=name,
            )
        traces.append(trace)

    if reference_point:
        if is_3d and z_key:
            ref_trace = go.Scatter3d(
                x=[reference_point[x_key]],
                y=[reference_point[y_key]],
                z=[reference_point[z_key]],
                mode="markers",
                marker={"size": 4, "color": "black", "symbol": "circle"},
                name="Reference Point",
            )
        else:
            ref_trace = go.Scatter(
                x=[reference_point[x_key]],
                y=[reference_point[y_key]],
                mode="markers",
                marker={"size": 8, "color": "black", "symbol": "circle"},
                name="Reference Point",
            )
        traces.append(ref_trace)

    return go.Figure(data=traces)
