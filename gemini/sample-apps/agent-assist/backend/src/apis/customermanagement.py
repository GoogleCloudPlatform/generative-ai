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
    filePath = "data/policy.json"
    with open(filePath) as json_file:
        data = json.load(json_file)

    startDate = request.args.get("startDate")
    endDate = request.args.get("endDate")
    if startDate is None or endDate is None:
        startDate = datetime.now() - timedelta(days=90)
        startDate = startDate.strftime("%Y-%m-%d")
        endDate = datetime.now().strftime("%Y-%m-%d")

    totalActiveCustomers, averageSatisfactionScore = getMetricsData(data, startDate, endDate)
    totalLapsedCustomers = getLapsedCustomers(data, startDate, endDate)
    chartData = getChartData(data, startDate, endDate)

    return (
        jsonify(
            {
                "totalActiveCustomers": totalActiveCustomers,
                "averageSatisfactionScore": float("{:.3}".format(averageSatisfactionScore)),
                "totalLapsedCustomers": totalLapsedCustomers,
                "chartData": chartData,
            }
        ),
        200,
    )


def getMetricsData(data: list, startDate: str, endDate: str):
    """
    This function is used to get the metrics data.

    Args:
        data (list): A list of dictionaries containing the policy data.
        startDate (str): The start date of the period for which the data is to be retrieved.
        endDate (str): The end date of the period for which the data is to be retrieved.

    Returns:
        tuple: A tuple containing the total number of active customers and the average satisfaction score.
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
            and policy_start_date >= startDate
            and policy_start_date <= endDate
        ):
            totalActiveCustomers += 1

    if totalratings != 0:
        averageSatisfactionScore = averageSatisfactionScore / totalratings

    return totalActiveCustomers, averageSatisfactionScore


def getLapsedCustomers(data: list, startDate: str, endDate: str):
    """
    This function is used to get the number of lapsed customers.

    Args:
        data (list): A list of dictionaries containing the policy data.
        startDate (str): The start date of the period for which the data is to be retrieved.
        endDate (str): The end date of the period for which the data is to be retrieved.

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
            and policy_end_date >= startDate
            and policy_end_date <= endDate
        ):
            totalLapsedCustomers += 1

    return totalLapsedCustomers


def getChartData(data: list, startDate: str, endDate: str):
    """
    This function is used to get the chart data.

    Args:
        data (list): A list of dictionaries containing the policy data.
        startDate (str): The start date of the period for which the data is to be retrieved.
        endDate (str): The end date of the period for which the data is to be retrieved.

    Returns:
        list: A list of dictionaries containing the chart data.
    """
    start_date = datetime.strptime(startDate, "%Y-%m-%d")
    end_date = datetime.strptime(endDate, "%Y-%m-%d")
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
            and policy_start_date >= startDate
            and policy_start_date <= endDate
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
