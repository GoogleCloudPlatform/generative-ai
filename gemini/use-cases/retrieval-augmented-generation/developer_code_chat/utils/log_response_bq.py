# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Log response to BigQuery table"""

import configparser

from google.cloud import bigquery


class LogDetailsInBQ:
    """Log Respose Details in BQ table"""

    def __init__(self, config_file: str = "config.ini") -> None:
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.project_id = self.config["default"]["project_id"]
        self.bq_table_id = self.config["log_response_in_bq"]["bq_table_id"]

    def save_response(self, question, intent, response, session_state):
        """Save user question and response"""
        try:
            client = bigquery.Client(project=self.project_id)
            rows_to_insert = [
                {
                    "question": question,
                    "intent": intent,
                    "assistant_response": response,
                    # "like_dislike": like_dislike,
                    # "feedback": feedback,
                    "session_id": session_state,
                }
            ]
            _ = client.insert_rows_json(self.bq_table_id, rows_to_insert)
            return "Your Feedback saved!"
        except Exception:  # pylint:disable=W0718,W0703
            return "Error in saving your feedback!"
