# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import json

from backend.app_logging import get_logger
from backend.app_settings import ApplicationSettings, get_application_settings

settings: ApplicationSettings = get_application_settings()  # type: ignore
logger = get_logger(__name__)


def appointment_scheduler():
    """
    Generates a structured JSON for the appointment scheduler UI.

    This function creates a mock schedule of available appointment slots with a
    financial advisor. The frontend can use this data to render an interactive
    scheduling component.

    Returns:
        A JSON string representing the appointment scheduler data.
    """
    scheduler_data = {
        "type": "appointment_scheduler",
        "title": "Schedule a consultation",
        "advisor": {
            "name": "Kevin",
            "title": "Senior Financial Advisor",
            "image": "/figma/andy.png",
        },
        "time_slots": [
            {
                "date": "Friday, Oct. 11",
                "slots": ["10:00 AM", "11:00 AM", "14:00 PM"],
            },
            {
                "date": "Monday, Oct. 14",
                "slots": ["10:00 AM", "11:00 AM", "14:00 PM"],
            },
            {
                "date": "Tuesday, Oct. 15",
                "slots": ["09:00 AM", "10:00 AM", "11:00 AM", "14:00 PM"],
            },
            {
                "date": "Wednesday, Oct. 16",
                "slots": ["10:00 AM", "11:00 AM"],
            },
        ],
        "confirmation": {
            "title": "Appointment Confirmed",
            "message": "Your appointment with Kevin is confirmed.",
            "button_text": "Close",
        },
    }
    return json.dumps(scheduler_data, indent=2)


def generate_financial_summary_visual():
    """
    Generates a structured JSON for the financial summary visual.

    This function creates a mock financial summary for a client. The frontend
    can use this data to render a financial summary component.

    Returns:
        A JSON string representing the financial summary data.
    """
    summary_data = {
        "type": "financial_summary_visual",
        "title": "Drew's Financial Summary",
        "totalBalance": {"currency": "USD"},
        "InvestmentPortfolio": {
            "ytd_return": 0.47,
            "positions": [
                {"symbol": "C", "marketValue": {"amount": 1500000}},
                {"symbol": "GOOGL", "marketValue": {"amount": 1000000}},
            ],
        },
    }
    return json.dumps(summary_data, indent=2)


def agent_execution_confirmation_notification():
    """
    Generates a structured JSON for a mock mobile notification UI.

    This function creates a mock notification to confirm that an agent action
    has been executed. The frontend can use this data to render a notification
    component that emulates the style of the appointment scheduler.

    Returns:
        A JSON string representing the mock notification data.
    """
    notification_data = {
        "type": "agent_execution_confirmation_notification",
        "title": "Revise Portfolio Allocation",
        "allocation": "$10,000.00",
        "to": "Suggested 6-month CD\n4% APY",
        "estimated_outcome": "Earn $2,000.00\nmore in annual interest",
    }
    return json.dumps(notification_data, indent=2)


def display_cd_information():
    """
    Generates a structured JSON for displaying consolidated CD information.

    This function returns data for both the client's current CD and
    available reinvestment options, allowing the frontend to render
    two distinct visuals.

    Returns:
        A JSON string representing the consolidated CD information.
    """
    cd_information_data = {
        "type": "cd_information",
        "title": "CD Information",
        "current_cd_data": {
            "type": "client_current_cd",
            "title": "Your Current CD Maturity",
            "current_cd": {
                "term": "3 Months",
                "apy": "3%",
                "balance": "$10,074.17",
            },
        },
        "reinvestment_options_data": {
            "type": "cd_options",
            "title": "Here are your options",
            "options": [
                {"term": "3 Month CD", "apy": "3.25%"},
                {"term": "4 Month CD", "apy": "3.5%"},
                {"term": "6 Month CD", "apy": "4%"},
            ],
        },
    }
    return json.dumps(cd_information_data, indent=2)
