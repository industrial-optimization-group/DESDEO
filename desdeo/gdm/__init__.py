"""Imports available from the desdeo-gdm package."""

__all__ = [
    "dict_of_rps_to_list_of_rps",
    "list_of_rps_to_dict_of_rps",
    "majority_rule",
    "plurality_rule",
]

from .gdmtools import (
    dict_of_rps_to_list_of_rps,
    list_of_rps_to_dict_of_rps,
)

from .voting_rules import (
    majority_rule,
    plurality_rule,
)
