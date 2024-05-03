"""This is a python utility file."""

# pylint: disable=E0401

from datetime import datetime, timedelta
import json

from flask import jsonify, request


def get_customer_management_data():
    """
    This function is used to get the customer management data.

    Args:
        None

    Returns:
        json: A JSON object containing the customer management data.
    """
    file_path = "data/policy.json"
    with open(file_path, encoding="UTF-8") as json_file:
        data = json.load(json_file)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date is None or end_date is None:
        start_date = datetime.now() - timedelta(days=90)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

    total_active_customers, average_satisfaction_score = get_metrics_data(
        data, start_date, end_date
    )
    total_lapsed_customers = get_lapsed_customers(data, start_date, end_date)
    chart_data = get_chart_data(data, start_date, end_date)

    return (
        jsonify(
            {
                "total_active_customers": total_active_customers,
                "average_satisfaction_score": float(f"{average_satisfaction_score:.3}"),
                "total_lapsed_customers": total_lapsed_customers,
                "chart_data": chart_data,
            }
        ),
        200,
    )


def get_metrics_data(data: list, start_date: str, end_date: str):
    """
    This function is used to get the metrics data.

    Args:
        data (list): A list of dictionaries containing the policy data.
        start_date (str): The start date of the period
          for which the data is to be retrieved.
        end_date (str): The end date of the period for which the data is to be retrieved.

    Returns:
        tuple: A tuple containing the total number of
          active customers and the average satisfaction score.
    """
    total_active_customers = 0
    average_satisfaction_score = 0.0
    total_ratings = 0
    for policy in data:
        policy_start_date = policy["policy_start_date"]

        if policy["satisfaction_score"]:
            average_satisfaction_score += policy["satisfaction_score"]
            total_ratings += 1

        if policy_start_date is None:
            continue
        if policy["current_policy"] and start_date <= policy_start_date <= end_date:
            total_active_customers += 1

    if total_ratings != 0:
        average_satisfaction_score = average_satisfaction_score / total_ratings

    return total_active_customers, average_satisfaction_score


def get_lapsed_customers(data: list, start_date: str, end_date: str):
    """
    This function is used to get the number of lapsed customers.

    Args:
        data (list): A list of dictionaries containing the policy data.
        start_date (str): The start date of the period for which the data is to be retrieved.
        end_date (str): The end date of the period for which the data is to be retrieved.

    Returns:
        int: The total number of lapsed customers.
    """
    total_lapsed_customers = 0
    for policy in data:
        policy_end_date = policy["policy_end_date"]
        if policy_end_date is None:
            continue
        if (
            policy["current_policy"] is None
            and start_date <= policy_end_date <= end_date
        ):
            total_lapsed_customers += 1

    return total_lapsed_customers


def get_chart_data(data, start_date, end_date):
    """
    This function is used to get the chart data.

    Args:
        data (list): A list of dictionaries containing the policy data.
        start_date (str): The start date of the period for which the data is to be retrieved.
        end_date (str): The end date of the period for which the data is to be retrieved.

    Returns:
        list: A list of dictionaries containing the chart data.
    """
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    month_list = [
        datetime.strptime(f"{year:02}-{month:02}", "%Y-%m").strftime("%b-%y")
        for year in range(start_date.year, end_date.year + 1)
        for month in range(
            start_date.month if year == start_date.year else 1,
            end_date.month + 1 if year == end_date.year else 13,
        )
    ]

    month_data = {}
    for month in month_list:
        month_data[month] = {"satisfaction_score": 0, "active_customers": 0, "count": 0}
    for policy in data:
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        month = datetime.strptime(policy_start_date, "%Y-%m-%d").strftime("%b-%y")
        if policy["satisfaction_score"]:
            if month in month_data:
                month_data[month]["satisfaction_score"] += policy["satisfaction_score"]
                month_data[month]["count"] += 1
            else:
                month_data[month] = {
                    "satisfaction_score": policy["satisfaction_score"],
                    "count": 1,
                }
        if policy["current_policy"] and start_date <= policy_start_date <= end_date:
            if month in month_data:
                month_data[month]["active_customers"] += 1
            else:
                month_data[month] = {"active_customers": 1}

    chart_data = []
    for month in month_list:
        chart_data.append(
            {
                "x": month,
                "y1": month_data[month]["active_customers"],
                "y2": (
                    month_data[month]["satisfaction_score"] / month_data[month]["count"]
                    if month_data[month]["count"] != 0
                    else 0
                ),
            }
        )
    return chart_data
