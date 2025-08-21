"""Deprecated module."""

import warnings

from desdeo.emo.methods.templates import EMOResult, template1, template2

warnings.warn(
    "The EMO methods in this module are deprecated and will be removed in a future release. "
    "Please use the methods in desdeo.emo.methods.templates instead.",
    DeprecationWarning,
    stacklevel=2,
)
