"""Functionalities related to managing and building the project."""

import shutil
import warnings


def _check_executables(executable_list):
    missing_executables = []
    for executable in executable_list:
        if shutil.which(executable) is None:
            missing_executables.append(executable)

    if missing_executables:
        warnings.warn(
            f"""
            \nThe following required highly recommended executables cannot be found: {", ".join(missing_executables)}\n
            DESDEO relies on powerful 3rd party solvers to solve multiobjective
            optimization problems.  Without these solvers, sub-optimal defaults
            will be used instead, which can lead to not optimal, or even wrong,
            results.\n
            It is highly recommended to have these solvers available
            in the environment DESDEO is utilized!\n
            For more information, see DESDEO's documentation: https://desdeo.readthedocs.io/en/latest/howtoguides/installing/#third-party-optimizers
            """,
            UserWarning,
            stacklevel=2,
        )
