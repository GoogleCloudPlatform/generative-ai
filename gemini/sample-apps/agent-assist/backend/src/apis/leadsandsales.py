"""This is a python utility file."""

from datetime import datetime, timedelta
import json
from typing import Any, Dict

from flask import jsonify, request


def formatINR(number) -> str:
    """
    Formats a number into Indian Rupee format.

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


def getLeadsAndSalesData() -> tuple[dict, int]:
    """
    Gets the leads and sales data from the JSON file.

    Returns:
        json: The leads and sales data in JSON format.
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

    conversionRate, leadsGenerated, revenueGenerated = getConversionRate(
        data, startDate, endDate
    )
    platformData, topPerformingPlatform = getDifferentPlatformData(
        data, startDate, endDate
    )
    topPerformingPolicy = getTopPerformingPolicy(data, startDate, endDate)

    return (
        jsonify(
            {
                "leadsGenerated": leadsGenerated,
                "conversionRate": conversionRate,
                "revenueGenerated": revenueGenerated,
                "platformData": platformData,
                "topPerformingPlatform": topPerformingPlatform,
                "topPerformingPolicy": topPerformingPolicy,
            }
        ),
        200,
    )


def getConversionRate(data: list, startDate: str, endDate: str) -> tuple:
    """
    Gets the conversion rate, leads generated, and revenue generated.

    Args:
        data (list): The list of policies.
        startDate (str): The start date.
        endDate (str): The end date.

    Returns:
        tuple: The conversion rate, leads generated, and revenue generated.
    """
    totalCount = 0
    count = 0
    revenue = 0
    for policy in data:
        last_contacted_data = policy["last_contacted"]
        if last_contacted_data is None:
            continue
        if last_contacted_data >= startDate and last_contacted_data <= endDate:
            totalCount += 1
            count += 1 if policy["converted"] else 0
            revenue += policy["policy_amount"] if policy["converted"] else 0

    return (
        float("{:.4}".format((count * 100) / totalCount)),
        totalCount,
        formatINR(revenue),
    )


def getDifferentPlatformData(data: list, startDate: str, endDate: str) -> tuple:
    """
    Gets the data for different platforms.

    Args:
        data (list): The list of policies.
        startDate (str): The start date.
        endDate (str): The end date.

    Returns:
        tuple: The chart data and the top performing platform.
    """
    finalData: Dict[str, Any] = {}
    for policy in data:
        last_contacted_data = policy["last_contacted"]
        if last_contacted_data is None:
            continue
        if last_contacted_data >= startDate and last_contacted_data <= endDate:
            if policy["platform"] in finalData:
                finalData[policy["platform"]]["count"] += 1
                finalData[policy["platform"]]["revenue"] += (
                    policy["policy_amount"] if policy["converted"] else 0
                )
            else:
                finalData[policy["platform"]] = {"count": 0, "revenue": 0}
    chartData = []
    topPerformingPlatform = max(finalData, key=lambda x: finalData[x]["revenue"])
    for key in finalData.keys():
        chartData.append(
            {"x": key, "y1": finalData[key]["count"], "y2": finalData[key]["revenue"]}
        )

    return chartData, topPerformingPlatform


def getTopPerformingPolicy(data: list, startDate: str, endDate: str) -> str:
    """
    Gets the top performing policy.

    Args:
        data (list): The list of policies.
        startDate (str): The start date.
        endDate (str): The end date.

    Returns:
        str: The top performing policy.
    """
    finalData: Dict[str, Any] = {}
    for policy in data:
        last_contacted_data = policy["last_contacted"]
        if last_contacted_data is None:
            continue
        if last_contacted_data >= startDate and last_contacted_data <= endDate:
            if policy["current_policy"] is None:
                continue
            if policy["current_policy"] in finalData:
                finalData[policy["current_policy"]] += 1
            else:
                finalData[policy["current_policy"]] = 1

    topPerformingPolicy = max(finalData, key=lambda x: finalData[x])

    return topPerformingPolicy
