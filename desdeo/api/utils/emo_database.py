"""Utility functions for EMO database operations."""

from typing import List
from sqlmodel import Session
from desdeo.api.models.archive import UserSavedEMOResults
from desdeo.api.models.state import StateDB

def _convert_dataframe_to_dict_list(df):
    """Convert DataFrame to list of dictionaries, handling different DataFrame types."""
    if df is None:
        return []

    # Check if it's a pandas DataFrame
    if hasattr(df, "iterrows"):
        return [row.to_dict() for _, row in df.iterrows()]

    # Check if it's a Polars DataFrame
    elif hasattr(df, "iter_rows"):
        # Get column names
        columns = df.columns
        return [dict(zip(columns, row)) for row in df.iter_rows()]

    # Check if it's already a list of dictionaries
    elif isinstance(df, list):
        return df

    # Check if it has to_dict method (pandas Series)
    elif hasattr(df, "to_dict"):
        return [df.to_dict()]

    # Try to convert to dict if it's a single row
    elif hasattr(df, "__iter__") and not isinstance(df, (str, dict)):
        try:
            # Assume it's iterable with column names
            if hasattr(df, "columns"):
                return [dict(zip(df.columns, row)) for row in df]
            else:
                # Generic conversion
                return [dict(enumerate(row)) for row in df]
        except Exception:
            pass

    # If all else fails, try to convert to string representation
    return [{"data": str(df)}]
