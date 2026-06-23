"""Deprecated module."""

import warnings

warnings.warn(
    "The EMO methods in this module are deprecated and will be removed in a future release. "
    "Please use the methods in desdeo.emo.methods.templates instead.",
    DeprecationWarning,
    stacklevel=2,
)
