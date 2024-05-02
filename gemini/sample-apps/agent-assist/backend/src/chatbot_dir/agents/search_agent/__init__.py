"""This is a python utility file."""

from .app.driver import Driver


def run(query, policy_list):
    driver = Driver()
    response = driver.run(query, policy_list)
    return response
