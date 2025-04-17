# ADK Multi-Agent MCP Client Application

## 1. Introduction

This chatbot demonstrates the use of the ADK Multi-Agent integrated with MCP Clients

Architecture:

![architecture](adk_multiagent.png)

It has three agents: root agent, cocktail agent, and booking agent.

It interacts with the following MCP servers:

- Cocktail MCP server (Local code) - 2. Weather MCP server (Local code)
- [Public Airbnb MCP server](https://github.com/openbnb-org/mcp-server-Airbnb) (Fetch code via Pypi)

- The Cocktail MCP server has 5 tools:

  - search cocktail by name
  - list all cocktail by first letter
  - search ingredient by name.
  - list random cocktails
  - lookup full cocktail details by ID

- The Weather MCP server has 3 tools:

  - get weather forecast by city name
  - get weather forecast by coordinates
  - get weather alert by state code

- The Airbnb MCP server has 2 tools:
  - search for Airbnb listings
  - get detailed information about a specific Airbnb listing

## 2. Example questions

Here are some example questions you can ask the chatbot:

- 'Please get cocktail margarita ID and then full detail of cocktail margarita'
- 'Please list a random cocktail'
- 'Please get weather forecast for New York'
- 'Please get weather forecast for 40.7128,-74.0060'
- 'I would like to book an Airbnb condo in LA, CA for 2 nights. 04/28 - 04/30, 2025, two adults, no kid'
