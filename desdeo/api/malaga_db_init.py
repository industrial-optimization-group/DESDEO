import json  # noqa: D100

from desdeo.api.db_init import *  # noqa: F403
from desdeo.utopia_stuff.utopia_problem import utopia_problem

with open("C:/MyTemp/code/students_and_passwords.json") as file:  # noqa: PTH123
    userdict = json.load(file)

db = SessionLocal()

holding_num = 1
for name in userdict:
    print(name)
    user = db_models.User(
        username=name,
        password_hash=get_password_hash(userdict[name]),
        role=UserRole.DM,
        privilages=[],
        user_group="",
    )
    db.add(user)

db.commit()

# Extra problem ends here

db.close()
