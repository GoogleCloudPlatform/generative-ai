"""This is a python utility file."""

from datetime import datetime, timedelta
import json
from typing import Any, Dict

from flask import jsonify, request


def format_inr(number) -> str:
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


def get_leads_and_sales_data() -> tuple[dict, int]:
    """
    Gets the leads and sales data from the JSON file.

    Returns:
        json: The leads and sales data in JSON format.
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

    conversion_rate, leads_generated, revenue_generated = get_conversion_rate(
        data, start_date, end_date
    )
    platform_data, top_performing_platform = get_different_platform_data(
        data, start_date, end_date
    )
    top_performing_policy = get_top_performing_policy(data, start_date, end_date)

    return (
        jsonify(
            {
                "leads_generated": leads_generated,
                "conversion_rate": conversion_rate,
                "revenue_generated": revenue_generated,
                "platform_data": platform_data,
                "top_performing_platform": top_performing_platform,
                "top_performing_policy": top_performing_policy,
            }
        ),
        200,
    )


def get_conversion_rate(data: list, start_date: str, end_date: str) -> tuple:
    """
    Gets the conversion rate, leads generated, and revenue generated.

    Args:
        data (list): The list of policies.
        start_date (str): The start date.
        end_date (str): The end date.

    Returns:
        tuple: The conversion rate, leads generated, and revenue generated.
    """
    total_count = 0
    count = 0
    revenue = 0
    for policy in data:
        last_contacted_data = policy["last_contacted"]
        if last_contacted_data is None:
            continue
        if last_contacted_data >= start_date and last_contacted_data <= end_date:
            total_count += 1
            count += 1 if policy["converted"] else 0
            revenue += policy["policy_amount"] if policy["converted"] else 0

    return (
        float("{:.4}".format((count * 100) / total_count)),
        total_count,
        format_inr(revenue),
    )


def get_different_platform_data(data: list, start_date: str, end_date: str) -> tuple:
    """
    Gets the data for different platforms.

    Args:
        data (list): The list of policies.
        start_date (str): The start date.
        end_date (str): The end date.

    Returns:
        tuple: The chart data and the top performing platform.
    """
    final_data: Dict[str, Any] = {}
    for policy in data:
        last_contacted_data = policy["last_contacted"]
        if last_contacted_data is None:
            continue
        if last_contacted_data >= start_date and last_contacted_data <= end_date:
            if policy["platform"] in final_data:
                final_data[policy["platform"]]["count"] += 1
                final_data[policy["platform"]]["revenue"] += (
                    policy["policy_amount"] if policy["converted"] else 0
                )
            else:
                final_data[policy["platform"]] = {"count": 0, "revenue": 0}
    chart_data = []
    top_performing_platform = max(final_data, key=lambda x: final_data[x]["revenue"])
    for key in final_data.keys():
        chart_data.append(
            {"x": key, "y1": final_data[key]["count"], "y2": final_data[key]["revenue"]}
        )

    return chart_data, top_performing_platform


def get_top_performing_policy(data: list, start_date: str, end_date: str) -> str:
    """
    Gets the top performing policy.

    Args:
        data (list): The list of policies.
        start_date (str): The start date.
        end_date (str): The end date.

    Returns:
        str: The top performing policy.
    """
    final_data: Dict[str, Any] = {}
    for policy in data:
        last_contacted_data = policy["last_contacted"]
        if last_contacted_data is None:
            continue
        if last_contacted_data >= start_date and last_contacted_data <= end_date:
            if policy["current_policy"] is None:
                continue
            if policy["current_policy"] in final_data:
                final_data[policy["current_policy"]] += 1
            else:
                final_data[policy["current_policy"]] = 1

    top_performing_policy = max(final_data, key=lambda x: final_data[x])

    return top_performing_policy
