# Problem access

Access to a problem can be granted by `role` or by `user id`. By `role`, all users that have the assigned role are able to access the problem. By `user id`, only the user with the assigned id can access the problem.

To grant access by `role`:

- Assign user role(s) (GUEST, DM, ANALYST) `desdeo/api/schema.py:UserRole` as an array to `role_permission` column in `Problem` table
```json
problem_in_db = db_models.Problem(
    ...
    role_permission=[UserRole.GUEST],
    ...
)
```
`UserRole.GUEST`: A UserRole object that indicates `guest` role

To grant access by `user id`: 

- Assign user's id to `user_id` column and problem's id to `problem_access` column in `UserProblemAccess` table
```json
userAccess = db_models.UserProblemAccess(
  user_id=$user.id,
  problem_access=$problem_id
)
```
`$user.id`: id of the user 
`$problem_id`: id of the problem

## How problems are fetched?

If the user is `analyst`, all problems will be fetched and sent to UI.

If the user is not `analyst`,

    - Firstly, all problems assigned to the user's role will be fetched (1)

    - Then, problems are fetched based on the user id (2)

    - Lastly, the API returns collection of problems that are joined by problems from (1), (2)



