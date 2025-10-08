"""Base classes for Group Decision Making. Here one can add some common data types for serialization."""

import json

from pydantic import ValidationError
from sqlalchemy.types import TypeDecorator
from sqlmodel import JSON, SQLModel

from desdeo.api.models.preference import ReferencePoint


class ReferencePointDictType(TypeDecorator):
    """A converter for dict of int and preferences."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, ReferencePoint):
                    value[key] = item.model_dump_json()
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        dictionary = json.loads(value)
        for key, item in dictionary.items():
            if item is None:
                print("Something's wrong... Database has a NoneType entry.")
            try:
                dictionary[key] = ReferencePoint.model_validate(json.loads(item))
            except ValidationError as e:
                print(f"Validation error when deserializing PreferencePoint: {e}")
        return dictionary


class BooleanDictTypeDecorator(TypeDecorator):
    """A converter of bool into json, surprising that this needs to exists."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, bool):
                    value[key] = json.dumps(item)
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        dictionary = json.loads(value)
        for key, item in dictionary.items():
            if item is None:
                print("Something's wrong... Database has a NoneType entry.")
            try:
                dictionary[key] = bool(item)
            except Exception as e:
                print(f"Validation error when deserializing boolean: {e}")
        return dictionary


class BasePreferences(SQLModel):
    """A base class for a method specific preference and results."""

    method: str = "unset"
