# Database models and schema

To interact with the underlying database in the DESDEO web-API, the
[SQLModel](https://sqlmodel.tiangolo.com/) library is used. It can be thought of
an abstraction that neatly combines [SQLAlchemy](https://www.sqlalchemy.org/)
with [Pydantic](https://docs.pydantic.dev/latest/) models.

What can initially feel confusing are the multiple SQLModels that are defined,
at face-value, for most part same purpose in the web-API. Before going into
details why things are structured as they are, we must understand the purposes
of the web-API. **The main purposes of the web-API are:**

1. retrieve and store data from and to a database, and
2. handle HTTP requests from clients (e.g., the DESDEO web-GUI) through its endpoints.

There are three types of SQLModels in the web-API, which serve the two listed
main purposes. Serving the first purpose are __table models__, while the second
purpose is served by __response and request models__.
These models also define the __schema__ of the data that is handled in various parts
of the web-API. We will cover each in the following sections.

!!! Note "Model vs schema"

    A __model__ represents data structures and logic within application code,
    including methods to interact with data, while a __schema__ defines the
    structure and organization of data, whether in a database or in HTTP
    request/response formats. In the context of databases, models use schemas to
    map application data structures to database structures. For HTTP endpoints,
    schemas define the expected format of request and response data, ensuring
    that communication between client and server adheres to a predefined
    structure, while models handle the logic and processing of this data within
    the application.

Here, we explain the main logic and purpose of these three types of models and the
schema they define in DESDEO's web-API.

## Table models

### The model

For the purpose of storing data in a database, we define **table models**. 
Table models are models that define the schema of data that we store in the database
managed by the web-API. These can be identified by the `table=True` parameter
given when defining new SQLModels. E.g.,in the class defining the model `User`
in `desdeo/api/models/user.py`:

```python
class User(UserBase, table=True):
    """The table model of an user stored in the database."""

    id: int | None = Field(primary_key=True, default=None)
    password_hash: str = Field()
    role: UserRole = Field()
    group: str = Field(default="")
    active_session_id: int | None = Field(default=None)

    # Back populates
    archive: list["ArchiveEntryDB"] = Relationship(back_populates="user")
    preferences: list["PreferenceDB"] = Relationship(back_populates="user")
    problems: list["ProblemDB"] = Relationship(back_populates="user")
    sessions: list["InteractiveSessionDB"] = Relationship(back_populates="user")
```

!!! Note "Why `UserBase`"

    Notice that `UserBase` is a class that inherits from the `SQLModel` class, i.e.:

    ```python
    class UserBase(SQLModel):
        """Base user model."""

        username: str = Field(index=True)
    ```

    but for now, we can think of `UserBase` to just be synonymous with `SQLModel` in the
    above example. We will return to the purpose of having something like `UserBase`
    when defining table models and other types of models later.

To see what will be stored in the database in case of the table model `User`, we
have defined multiple class variables with the `Field` class imported from
SQLModel. We will refer to these just as __fields__. 
The fields of the `User` table model are `id` (the primary key, i.e.., unique
identifier of a user), `password_hash` (the hashed password of a user), `role`
(the role/privileges of a user), `group` (the group of a user), and
`active_session_id` (the identifier of the currently active session of a user).
Additionally, `User` has also the field `username`, which is derived
from the parent class `UserBase`. To put this into the context of a database,
we can think of the table model `User` as the
__rows__ in a database, while the fields listed above can be thought of
the __columns__:

| id | password_hash | role  | group  | active_session_id |
|----|---------------|-------|--------|-------------------|
| 1  | abc123        | admin | group1 | 101               |
| 2  | def456        | dm    | group1 | 102               |
| 3  | ghi789        | guest | group2 | NULL              |


In addition,
we have also defined __relationships__ with other table models in the database
using the `Relationship` class imported from SQLModel. These relationships
are `archive`, `preferences`, `problems`, and `sessions`. These table models will
have a foreign key, which will have the value of the user's id the table model is related
to. In the case of the listed relationships, the `User` model is the __parent__ while
`archive`, `preferences`, `problems` and `sessions` are its children. Notice that the
`User` might have multiple children of the same type, e.g., `problem`.

### Storing table models to the database

To store table models to a database, we first need to create an instance of the model.
Continuing with the `User` model as an example, we can create an instance of the model
as follows:

```python
user_example = User(
    username="Decision maker",
    password_hash=get_password_hash("example_password"),
    role=UserRole.dm,
    group="example",
)
```

Notice that we did not have to supply an `id` since this being a primary key,
will be created automatically once the `user_example` is added to the database.
Because SQLModel utilizes Pydantic, our model is also validated when created,
which means that the field values (which correspond to rows of the `User` table
model) we supply, are checked for their correct type.

To add `user_example` to a database, we need to have access to a __database session__, which
allows us to interact with the database. In the web-API, this session is automatically
made available in the context of HTTP endpoints, also known as routers. Assuming we do
have a database session '`session`' available, we can add `user_example` to it:

```python
session.add(example_user)
session.commit()
```

The `session.add` method alone is not enough as it only _stages_ the changes to
the database in memory. To write the changes, we need to commit them by calling
`session.commit`. This way we may stage multiple changes to the database in memory, e.g.,
when adding multiple new users, and then commit (write) the changes to the
database at once. This can minimize costly and blocking I/O interactions with the
database.

!!! Note "How to get a database session?"

    As mentioned, in the routers defined in the web-API, sessions are available
    automatically.  In many of the functions that define endpoints, we will see
    the syntax `session: Annotated[Session, Depends(get_session)]` in the arguments.
    For instance:

    ```python
    @router.post("/solve")
    def solve_solutions(
        request: RPMSolveRequest,
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
    ) -> RPMState:
        ...
    ```

    Without going too much into details, it is enough to understand that each
    time an endpoint with such syntax is called, the value for the `session`
    argument is retrieved by calling the function `get_session`, which will
    yield a database session that can then be used to interact with the
    database.  To see how a database session is created, the interested reader
    can refer to the file `desdeo/api/db.py`. The same principle applies in this
    example for the `user` argument as well, which is handled by the function
    `get_current_user`.

### Reading table models from a database

To read existing table models from a database we will once again assume
that a database session '`session`' is available. Assuming the `id` of
`example_user` is `1`, we can retrieve `example_user` using the
function `sqlmodel.select`:

```python
statement = select(User).where(User.id == 1)
user_from_db = session.exec(statement).first()
```

This is a fairly common pattern where we first define a query statement and then
execute it to retrieve its results (query result) from the database. Notice that we passed
the table model's class we wish to retrieve from the database to `select`, and then specified
we want to select all users with their `id` value equal to 1. When executed,
`session.exec` will return a list. Since we know that the `id` of each user is unique,
at most one user will be returned (in this case `example_user`), so calling
the method `first` on the query result is sufficient. If an user with `id=1`
would have not existed, `None` would have been returned.

Similarly, we could have queried the database for all users with the group `group1`:

```python
statement = select(User).where(User.group == "group1")
group1_users_from_db = session.exec(statement).all()
```

Now we have called the method `all` on the query result, which will either
return `None` if no users in the database exist with `group="group1"`, or it
will return a list of all the users (one or more) with `group="group1"`. Calling
`first` like in the previous example would not make sense now, unless we
specifically want the first user in the list.

We could also get all users with `group="group1"` and `role="admin"`:

```python
statement = select(User).where(User.group == "group1", User.role="admin")
group1_admins = session.exec(statement).all()
```

Similarly, more refined queries with many more predicates can be formulated.


!!! Note "Alternative syntax for retrieving data"

    In the preceding examples we utilized `sqlmodel.select` to formulate queries.
    Alternatively, we could have also written

    ```python
    user_from_db = session.get(User, 1)
    ```

    where the `get` method fetches the database entry of the table model `User`
    with the matching primary key, e.g., `id=1`. In fact, we could also use the
    SQLAlchemy version of `select` to query the database, but this is often more
    cumbersome than using `sqlmodel.select`, which is specifically for handling
    table models defined using SQLModel.

    However, for more advanced queries, SQLAlchemy can be used directly, and
    it can offer powerful tools in some cases. You can read more in the SQLAlchemy
    [Session API docs](https://docs.sqlalchemy.org/en/20/orm/session_api.html#session-api).

## Response and request models

### Response models

In addition to table models, SQLModel is used to define so-called
__response models__. These can be thought as a kind of _view_ 
of a specific table model. Returning to the `User` example
from the [table models section](#table-models), we have the
response model `UserPublic` defined as:

```python
class UserPublic(UserBase):
    """The object to handle public user information."""

    id: int
    role: UserRole
    group: str
```

First, we note that the previously defined class argument `table` is now
missing (it defaults to false), which means this is not a table model.
`UserPublic` also derives from the previously seen `UserBase` class.
Having a base class for the various models is a common design pattern
in the web-API. Base classes are used to define fields that
are common across the three kind of models in the web-API. They do not fall
in any of the specific categories themselves (table model, response model, or
request model); but are instead separate constructs to help define the
other models.

Second, we note that the fields in the response schema `UserPublic` consist
of a sub-group of the attributes defined for `User`, namely,
`id`, `role`, and `group`. The username is also available through the parent
class `UserBase`.

But what is the point of all of this? To understand the motivation for
response models, let us consider the router `get_current_user_info`:

```python
@router.get("/user_info")
def get_current_user_info(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    """Return information about the current user.

    Args:
        user (Annotated[User, Depends): user dependency, handled by `get_current_user`.

    Returns:
        UserPublic: public information about the current user.
    """
    return user
```

As was the case with the database session, we get automatically the `user` defined
as an argument to the endpoint through the function `get_current_user`. However,
if we look at what `get_current_user` returns, it returns an object
of type `User`, yet the endpoint `get_current_user` is supposed to
return the response model `UserPublic`. What gives?

What happens is that the `user` returned by `get_current_user` is used to
instantiate a response model of type `UserPublic` when returned. In other words,
we only grab the fields from the `user` object (which is of type `User`)
that are present in `UserPublic`, and return those to the frontend application
calling the web-API. Which is automagically handled by FastAPI, which
is used to define the endpoints. The schema of the returned model will look like follows:

```json
{
    "username": "string",
    "id": 0,
    "role": "guest",
    "group": "string"
}
```

The above information is all the information we wish to return about the current
user through the endpoint `get_current_user_info`, and that information is
defined by the response model associated with the return type of the endpoint.
This way we can exclude information, such as `password_hash`, which we might not
wish to return to the client as part of the response provided for the current
user.

To put it simply,
**we utilize response models to define what information we wish to return from
the endpoints defined in the web-API.** We could define these models returned by
each endpoint manually, but by utilizing response models, we can utilize already
defined table models (and other SQLModels) instead, saving time and reducing the
risk of introducing needless bugs.

### Request models

The last type of model to be covered are __request models__. Unlike table models
and response models, request models are used to define what information clients
of the web-API need to provide when accessing each endpoint.

For instance, the `solve_solutions` endpoint defined for the reference point method
is defined as follows:

```python
@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMState:
    ...
```

The content the client must explicitly provide is `request`, which is of
type `RPMSolveRequest`. Looking at the definition of this
 __request model__:

```python
class RPMSolveRequest(SQLModel):
    """Model of the request to the reference point method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    preference: ReferencePoint = Field(Column(JSON))
```

 we see that the endpoint expects a JSON object with the following schema:

```json
{
    "problem_id": 0,
    "session_id": null,
    "parent_state_id": null,
    "scalarization_options": null,
    "solver": null,
    "solver_options": null,
    "preference": {
        "preference_type": "string",
        "aspiration_levels": {}
    }
}
```

This simply means that request models are SQLModels that we define to specify what
kind of data an endpoint expects when accessed.

## Wrapping things up

To summarize, the three main type of model and their purpose in DESDEO's web-API are:

- __table models__: used to define the schema of data stored in the database of the web-API,
- __response models__: used to define the schema of data returned by the web-API's endpoints, and
- __request models__: used to define the schema of data expected by the web-API's endpoints.

This structure helps in separating concerns, making the codebase (hopefully!) more
maintainable and easier to understand. The table models handle database
operations, while the response and request models manage the data flow for HTTP
interactions between the web-API and client applications.