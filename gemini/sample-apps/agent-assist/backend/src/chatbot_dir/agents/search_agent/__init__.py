"""This is a python utility file."""

# pylint: disable=E0401

from .app.driver import Driver


def run(query, policy_list):
    """
    Driver function
    """

    driver = Driver()
    response = driver.run(query, policy_list)
    return response
