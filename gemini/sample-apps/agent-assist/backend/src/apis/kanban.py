import json
from datetime import datetime
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

    filePath = "data/real_users_db.json"
    with open(filePath) as json_file:
        data = json.load(json_file)

    # Create a dictionary of users, where the key is the user ID and the value is the user data.
    userData: Dict[str, Any] = {str(user["userid"]): user for user in data}

    # Create a dictionary of the kanban board, where the key is the column name and the value is a list of user IDs.
    finalData: Dict[str, Any] = {
        "initial-contact": [],
        "needs-analysis": [],
        "proposal-sent": [],
        "followup": [],
        "closed": [],
        "users": userData,
    }

    # Iterate over the users and add them to the appropriate column in the kanban board.
    for user in data:
        if not user["LastContacted"]:
            finalData["initial-contact"].append(str(user["userid"]))
        elif user["NeedsAnalysis"]:
            finalData["needs-analysis"].append(str(user["userid"]))
        elif user["ProposalSent"]:
            finalData["proposal-sent"].append(str(user["userid"]))
        elif user["converted"]:
            finalData["closed"].append(str(user["userid"]))
        else:
            finalData["followup"].append(str(user["userid"]))

    # Return the kanban board data as a JSON response.
    return jsonify(finalData), 200


def update_kanban_data() -> tuple[dict, int]:
    """
    This function updates the kanban board by moving a user from one column to another.
    It reads the data from a JSON file, updates the user's column, and writes the updated data to the JSON file.

    Args:
        None
    Returns:
        JSON response with a success message.

    """

    fromCol = request.json["fromCol"]
    toCol = request.json["toCol"]
    userid = request.json["id"]
    print(fromCol, toCol, userid)

    # Read the kanban board data from the JSON file.
    filePath = "data/real_users_db.json"
    with open(filePath) as json_file:
        data = json.load(json_file)

    # Find the user in the data and update their column.
    for user in data:
        if str(user["userid"]) == userid:
            if fromCol == "initial-contact":
                user["LastContacted"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if toCol == "initial-contact":
                user["LastContacted"] = None
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = False
                user["converted"] = False

            if toCol == "needs-analysis":
                user["NeedsAnalysis"] = True
                user["ProposalSent"] = False
                user["converted"] = False

            elif toCol == "proposal-sent":
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = True
                user["converted"] = False

            elif toCol == "followup":
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = False
                user["converted"] = False

            elif toCol == "closed":
                user["NeedsAnalysis"] = False
                user["ProposalSent"] = False
                user["converted"] = True
            break

    # Write the updated data to the JSON file.
    with open(filePath, "w") as json_file:
        json.dump(data, json_file)

    # Return a success message as a JSON response.
    return jsonify({"message": "updated"}), 200
