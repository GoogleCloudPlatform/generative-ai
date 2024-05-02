"""This is a python utility file."""

# pylint: disable=E0401

from datetime import datetime
import json
from typing import Any, Dict

from flask import jsonify, request


def get_kanban_data() -> tuple[dict, int]:
    """
    Get the current state of the kanban board.

    Args:
        None

    Returns:
        JSON response with the current state of the kanban board.
    """

    file_path = "data/real_users_db.json"
    with open(file_path, encoding="UTF-8") as json_file:
        data = json.load(json_file)

    # Create a dictionary of users, where the key is the user ID and the value is the user data.
    user_data: Dict[str, Any] = {str(user["userid"]): user for user in data}

    final_data: Dict[str, Any] = {
        "initial-contact": [],
        "needs-analysis": [],
        "proposal-sent": [],
        "followup": [],
        "closed": [],
        "users": user_data,
    }

    # Iterate over the users and add them to the appropriate column in the kanban board.
    for user in data:
        if not user["LastContacted"]:
            final_data["initial-contact"].append(str(user["userid"]))
        elif user["NeedsAnalysis"]:
            final_data["needs-analysis"].append(str(user["userid"]))
        elif user["ProposalSent"]:
            final_data["proposal-sent"].append(str(user["userid"]))
        elif user["converted"]:
            final_data["closed"].append(str(user["userid"]))
        else:
            final_data["followup"].append(str(user["userid"]))

    # Return the kanban board data as a JSON response.
    return jsonify(final_data), 200


def update_kanban_data() -> tuple[dict, int]:
    """
    This function updates the kanban board by moving a user from one column to another.
    It reads the data from a JSON file, updates the user's column, and
      writes the updated data to the JSON file.

    Args:
        None
    Returns:
        JSON response with a success message.

    """

    from_col = request.json["from_col"]
    to_col = request.json["to_col"]
    userid = request.json["id"]
    print(from_col, to_col, userid)

    # Read the kanban board data from the JSON file.
    file_path = "data/real_users_db.json"
    with open(file_path, encoding="UTF-8") as json_file:
        data = json.load(json_file)

    # Find the user in the data and update their column.
    for user in data:
        if str(user["userid"]) == userid:
            if from_col == "initial-contact":
                user["LastContacted"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if to_col == "initial-contact":
                user["LastContacted"] = None
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = False
                user["converted"] = False

            if to_col == "needs-analysis":
                user["NeedsAnalysis"] = True
                user["ProposalSent"] = False
                user["converted"] = False

            elif to_col == "proposal-sent":
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = True
                user["converted"] = False

            elif to_col == "followup":
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = False
                user["converted"] = False

            elif to_col == "closed":
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = False
                user["converted"] = True
            break

    # Write the updated data to the JSON file.
    with open(file_path, "w", encoding="UTF-8") as json_file:
        json.dump(data, json_file)

    # Return a success message as a JSON response.
    return jsonify({"message": "updated"}), 200
