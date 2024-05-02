"""This is a python utility file."""

from datetime import datetime, timedelta
import json

from flask import jsonify, request


def getCustomerManagementData():
    """
    This function is used to get the customer management data.

    Args:
        None

    Returns:
        json: A JSON object containing the customer management data.
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

    totalActiveCustomers, averageSatisfactionScore = getMetricsData(
        data, start_date, end_date
    )
    totalLapsedCustomers = getLapsedCustomers(data, start_date, end_date)
    chartData = getChartData(data, start_date, end_date)

    return (
        jsonify(
            {
                "totalActiveCustomers": totalActiveCustomers,
                "averageSatisfactionScore": float(
                    "{:.3}".format(averageSatisfactionScore)
                ),
                "totalLapsedCustomers": totalLapsedCustomers,
                "chartData": chartData,
            }
        ),
        200,
    )


def getMetricsData(data: list, start_date: str, end_date: str):
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
    totalActiveCustomers = 0
    averageSatisfactionScore = 0.0
    totalratings = 0
    for policy in data:
        policy_start_date = policy["policy_start_date"]

        if policy["satisfaction_score"]:
            averageSatisfactionScore += policy["satisfaction_score"]
            totalratings += 1

        if policy_start_date is None:
            continue
        if (
            policy["current_policy"]
            and policy_start_date >= start_date
            and policy_start_date <= end_date
        ):
            totalActiveCustomers += 1

    if totalratings != 0:
        averageSatisfactionScore = averageSatisfactionScore / totalratings

    return totalActiveCustomers, averageSatisfactionScore


def getLapsedCustomers(data: list, start_date: str, end_date: str):
    """
    This function is used to get the number of lapsed customers.

    Args:
        data (list): A list of dictionaries containing the policy data.
        start_date (str): The start date of the period for which the data is to be retrieved.
        end_date (str): The end date of the period for which the data is to be retrieved.

    Returns:
        int: The total number of lapsed customers.
    """
    totalLapsedCustomers = 0
    for policy in data:
        policy_end_date = policy["policy_end_date"]
        if policy_end_date is None:
            continue
        if (
            policy["current_policy"] is None
            and policy_end_date >= start_date
            and policy_end_date <= end_date
        ):
            totalLapsedCustomers += 1

    return totalLapsedCustomers


def getChartData(data: list, start_date: str, end_date: str):
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
        datetime.strptime("%2.2d-%2.2d" % (year, month), "%Y-%m").strftime("%b-%y")
        for year in range(start_date.year, end_date.year + 1)
        for month in range(
            start_date.month if year == start_date.year else 1,
            end_date.month + 1 if year == end_date.year else 13,
        )
    ]

    monthData = {}
    for month in month_list:
        monthData[month] = {"satisfaction_score": 0, "active_customers": 0, "count": 0}
    for policy in data:
        policy_start_date = policy["policy_start_date"]
        if policy_start_date is None:
            continue
        month = datetime.strptime(policy_start_date, "%Y-%m-%d").strftime("%b-%y")
        if policy["satisfaction_score"]:
            if month in monthData:
                monthData[month]["satisfaction_score"] += policy["satisfaction_score"]
                monthData[month]["count"] += 1
            else:
                monthData[month] = {
                    "satisfaction_score": policy["satisfaction_score"],
                    "count": 1,
                }
        if (
            policy["current_policy"]
            and policy_start_date >= start_date
            and policy_start_date <= end_date
        ):
            if month in monthData:
                monthData[month]["active_customers"] += 1
            else:
                monthData[month] = {"active_customers": 1}

    chartData = []
    for month in month_list:
        chartData.append(
            {
                "x": month,
                "y1": monthData[month]["active_customers"],
                "y2": (
                    monthData[month]["satisfaction_score"] / monthData[month]["count"]
                    if monthData[month]["count"] != 0
                    else 0
                ),
            }
        )
    return chartData
