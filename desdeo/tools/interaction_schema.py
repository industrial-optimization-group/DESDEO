"""The schema to represent the interactions of the user."""

from pydantic import BaseModel, Field


class Interaction(BaseModel):
    """The tree-like structure to represent the interactions of the user."""

    method_name: str = Field(description="The name of the method used for this iteration.")
    preference_information: dict = Field(description="The preference information given by the user for this iteration.")
    result: dict = Field(
        description="The result of the iteration."
    )  # In the database, this should be a foreign key to the result table
    next_interaction: list["Interaction"] | None = Field(
        "The next interaction in the tree. This is a list of 'interactions' as the user can choose to go back to a"
        " previous iteration and change the preference information. If the user chooses to go back, just append the"
        " new interactions to the list in the order they were made."
    )  # In the database, this should be a foreign key to the interactions table


if __name__ == "__main__":
    # An example of how to use the schema
    inter = Interaction(
        method_name="NIMBUS",
        preference_information={"a": 1},
        result={"foo": [0, 0, 1]},
        next_interaction=[
            Interaction(
                method_name="iRVEA",
                preference_information={"b": [1, 2]},
                result={"baz": [9, 1, 0]},
                next_interaction=None,
            )
        ],
    )
    print(inter.model_dump_json())
    print()
    print(Interaction.model_json_schema())
