"""This is a python utility file."""

# pylint: disable=E0401

from datetime import datetime, timedelta
import json
from typing import Any, Dict

from flask import jsonify, request


def format_inr(num):
    """
    Formats the given number to Indian Rupee format.

    Args:
        num (int): The number to be formatted.

    Returns:
        str: The formatted number in Indian Rupee format.
    """
    if num > 10000000:
        return "₹" + f"{num / 10000000:.4}" + "Cr"
    if num > 100000:
        return "₹" + f"{num / 100000:.4}" + "L"
    if num > 1000:
        return "₹" + f"{num / 1000:.4}" + "K"

    return "₹" + str(num)


def get_performance_data():
    """
    Gets the performance data from the JSON file.

    Returns:
        json: The performance data in JSON format.
    """
    file_path = "data/policy.json"
    with open(file_path, encoding="UTF-8") as json_file:
        data = json.load(json_file)

    begin_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if begin_date is None or end_date is None:
        begin_date = datetime.now() - timedelta(days=90)
        begin_date = begin_date.strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

    return (
        jsonify(
            {
                "number_of_policies_sold": get_number_of_policies_sold(
                    data, begin_date, end_date
                ),
                "revenue_generated": format_inr(
                    get_revenue_generated(data, begin_date, end_date)
                ),
                "renewal_rate": get_renewal_rate(data, begin_date, end_date),
                "month_data": get_month_data(data, begin_date, end_date),
            }
        ),
        200,
    )


# get_number_of_policies_sold


def get_number_of_policies_sold(data: list, start_date: str, end_date: str) -> int:
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
        if start_date <= policy_start_date <= end_date:
            count += 1
    return count


def get_revenue_generated(data: list, start_date: str, end_date: str) -> float:
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
        if start_date <= policy_start_date <= end_date:
            revenue += policy["policy_amount"]
    return revenue


def get_renewal_rate(data: list, start_date: str, end_date: str) -> float:
    """
    Gets the renewal rate between the given start and end dates.

    Args:
        data (list): The list of policies.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        float: The renewal rate between the given start and end dates.
    """
    total_policies = 0
    policies_renewed = 0
    for policy in data:
        total_policies += 1
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        if (
            start_date <= policy_start_date <= end_date
            and policy["current_policy"] == policy["old_policy"]
        ):
            policies_renewed += 1

    return float(f"{(policies_renewed * 100) / total_policies:.4}")


def get_month_data(data, start_date, end_date):
    """
    Gets the month wise policy sold and revenue during the given period

    Args:
        data (list): The list of policies.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        list: The month wise policy sold and revenue during the given period
    """
    month_data: Dict[str, Any] = {}

    # Get month wise policy sold and revenue during the given period
    for policy in data:
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        if start_date <= policy_start_date <= end_date:
            month = datetime.strptime(policy_start_date, "%Y-%m-%d").strftime("%b-%y")
            if month in month_data:
                month_data[month]["policies_sold"] += 1
                month_data[month]["revenue"] += policy["policy_amount"]
            else:
                month_data[month] = {
                    "policies_sold": 1,
                    "revenue": policy["policy_amount"],
                }

    # Get month list
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    month_list = [
        datetime.strptime(f"{year:02d}-{month:02d}", "%Y-%m").strftime("%b-%y")
        for year in range(start_date.year, end_date.year + 1)
        for month in range(
            start_date.month if year == start_date.year else 1,
            end_date.month + 1 if year == end_date.year else 13,
        )
    ]

    final_data = []
    for month in month_list:
        if month not in month_data:
            final_data.append({"x": month, "y1": 0, "y2": 0})
            continue
        final_data.append(
            {
                "x": month,
                "y1": month_data[month]["policies_sold"],
                "y2": month_data[month]["revenue"],
            }
        )
    return final_data
