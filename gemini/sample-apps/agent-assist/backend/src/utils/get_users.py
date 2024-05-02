"""This is a python utility file."""

# pylint: disable=E0401

import json


def get_users(isContact: bool = True) -> list:
    """Gets a list of users from a JSON file.

    Args:
    isContact: A boolean value indicating whether to return users who have been contacted or not.

    Returns:
    A list of dictionaries representing users.
    """

    with open("data/real_users_db.json") as f:
        users = json.load(f)

    if isContact:
        contacted_users = list(filter(lambda x: x["LastContacted"] is not None, users))
        return contacted_users
    else:
        potential_users = list(filter(lambda x: x["LastContacted"] is None, users))
        return potential_users


if __name__ == "__main__":
    print(get_users())
