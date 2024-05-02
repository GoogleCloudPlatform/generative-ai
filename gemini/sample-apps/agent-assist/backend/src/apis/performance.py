"""This is a python utility file."""

from datetime import datetime, timedelta
import json
from typing import Any, Dict

from flask import jsonify, request


def format_inr(number):
    """
    Formats the given number to Indian Rupee format.

    Args:
        number (int): The number to be formatted.

    Returns:
        str: The formatted number in Indian Rupee format.
    """
    if number > 10000000:
        return "₹" + "{:.4}".format(number / 10000000) + "Cr"
    elif number > 100000:
        return "₹" + "{:.4}".format(number / 100000) + "L"
    elif number > 1000:
        return "₹" + "{:.4}".format(number / 1000) + "K"
    else:
        return "₹" + str(number)


def getPerformanceData():
    """
    Gets the performance data from the JSON file.

    Returns:
        json: The performance data in JSON format.
    """
    file_path = "data/policy.json"
    with open(file_path) as json_file:
        data = json.load(json_file)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date is None or end_date is None:
        start_date = datetime.now() - timedelta(days=90)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

    return (
        jsonify(
            {
                "numberOfPoliciesSold": getNumberOfPoliciesSold(
                    data, start_date, end_date
                ),
                "revenue_generated": format_inr(
                    getrevenue_generated(data, start_date, end_date)
                ),
                "renewalRate": getRenewalRate(data, start_date, end_date),
                "monthData": getMonthData(data, start_date, end_date),
            }
        ),
        200,
    )


# getNumberOfPoliciesSold


def getNumberOfPoliciesSold(data: list, start_date: str, end_date: str) -> int:
    """
    Gets the number of policies sold between the given start and end dates.

    Args:
        data (list): The list of policies.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        int: The number of policies sold between the given start and end dates.
    """
    count = 0
    for policy in data:
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        if policy_start_date >= start_date and policy_start_date <= end_date:
            count += 1
    return count


def getrevenue_generated(data: list, start_date: str, end_date: str) -> float:
    """
    Gets the revenue generated between the given start and end dates.

    Args:
        data (list): The list of policies.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        float: The revenue generated between the given start and end dates.
    """
    revenue = 0
    for policy in data:
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        if policy_start_date >= start_date and policy_start_date <= end_date:
            revenue += policy["policy_amount"]
    return revenue


def getRenewalRate(data: list, start_date: str, end_date: str) -> float:
    """
    Gets the renewal rate between the given start and end dates.

    Args:
        data (list): The list of policies.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        float: The renewal rate between the given start and end dates.
    """
    totalPolicies = 0
    policiesRenewed = 0
    for policy in data:
        totalPolicies += 1
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        if (
            policy_start_date >= start_date
            and policy_start_date <= end_date
            and policy["current_policy"] == policy["old_policy"]
        ):
            policiesRenewed += 1

    return float("{:.4}".format((policiesRenewed * 100) / totalPolicies))


def getMonthData(data: list, start_date: str, end_date: str) -> list:
    """
    Gets the month wise policy sold and revenue during the given period

    Args:
        data (list): The list of policies.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        list: The month wise policy sold and revenue during the given period
    """
    monthData: Dict[str, Any] = {}

    # Get month wise policy sold and revenue during the given period
    for policy in data:
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        if policy_start_date >= start_date and policy_start_date <= end_date:
            month = datetime.strptime(policy_start_date, "%Y-%m-%d").strftime("%b-%y")
            if month in monthData:
                monthData[month]["policiesSold"] += 1
                monthData[month]["revenue"] += policy["policy_amount"]
            else:
                monthData[month] = {
                    "policiesSold": 1,
                    "revenue": policy["policy_amount"],
                }

    # Get month list
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    month_list = [
        datetime.strptime("%2.2d-%2.2d" % (year, month), "%Y-%m").strftime("%b-%y")
        for year in range(start_date.year, end_date.year + 1)
        for month in range(
            start_date.month if year == start_date.year else 1,
            end_date.month + 1 if year == end_date.year else 13,
        )
    ]

    final_data = []
    for month in month_list:
        if month not in monthData:
            final_data.append({"x": month, "y1": 0, "y2": 0})
            continue
        final_data.append(
            {
                "x": month,
                "y1": monthData[month]["policiesSold"],
                "y2": monthData[month]["revenue"],
            }
        )
    return final_data


if __name__ == "__main__":
    file_path = "../data/policy.json"
    with open(file_path) as json_file:
        data = json.load(json_file)
    getMonthData(data, "2022-01-01", "2023-12-31")
