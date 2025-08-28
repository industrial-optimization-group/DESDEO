"""Base classes for Group Decision Making. Here one can add some common data types for serialization"""

import json

from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel, JSON
from pydantic import ValidationError

from desdeo.api.models import ReferencePoint
from desdeo.tools import SolverResults

class SolverResultType(TypeDecorator):
    """Dunno why the solver results wouldn't serialize but this should do the trick"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, list):
            solver_list = []
            for item in value:
                if isinstance(item, SolverResults):
                    solver_list.append(item.model_dump_json())
            return json.dumps(solver_list)
    
    def process_result_value(self, value, dialect):
        if value is not None:
            value_list = json.loads(value)
            solver_list: SolverResults = []
            for item in value_list:
                item_dict = json.loads(item)
                try:
                    solver_list.append(SolverResults.model_validate(item_dict))
                except ValidationError as e:
                    print(f"Validation error when deserializing SolverResults: {e}")
                    continue
            return solver_list
        
class ReferencePointDictType(TypeDecorator):
    """A converter for dict of int and preferences"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, ReferencePoint):
                    value[key] = item.model_dump_json()
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        dictionary = json.loads(value)
        for key, item in dictionary.items():
            if item == None:
                print("Something's wrong... Database has a NoneType entry.")
            try:
                dictionary[key] = ReferencePoint.model_validate(json.loads(item))
            except ValidationError as e:
                print(f"Validation error when deserializing PreferencePoint: {e}")
        return dictionary

class BasePreferenceResults(SQLModel):
    """A base class for a method specific preference and results"""
    method: str = "unset"
