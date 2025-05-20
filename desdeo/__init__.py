"""Configuration stuff of the DESDEO framework."""

from desdeo.core import _check_executables

# List of required executables
required_executables = ["bonmin", "cbc", "ipopt"]

# Check for executables when the library is imported
_check_executables(required_executables)
