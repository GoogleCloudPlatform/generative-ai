# FILE: harness/tool_mapper.py

def map_airline_arguments(adk_tool_name: str, adk_args: dict) -> dict:
    """
    Translates arguments from ADK tool format to Tau2 tool format for the airline domain.
    For our current example, the argument names match, so we can just return them.
    If they were different, you would add mapping logic here.
    e.g., if adk_args had 'from_city', you'd map it to 'origin'.
    """
    return adk_args

# --- The Central Mapping Configuration ---
# To support a new domain, add a new entry here.
DOMAIN_CONFIGS = {
    "airline": {
        "tool_map": {
            # ADK Tool Name : Tau2 Tool Name
            "adk_find_flights": "search_direct_flight",
            "adk_get_booking_details": "get_reservation_details",
            "adk_cancel_reservation": "cancel_reservation",
            "adk_transfer_to_human": "transfer_to_human_agents",
        },
        "arg_mapper": map_airline_arguments
    },
    # "telecom": { ... mappings for telecom would go here ... }
}

def get_tool_mapping(domain: str) -> dict:
    """
    Returns the tool and argument mapping configuration for a given domain.
    """
    if domain in DOMAIN_CONFIGS:
        return DOMAIN_CONFIGS[domain]
    else:
        raise ValueError(f"No tool mapping is configured for domain: '{domain}'. Please add it to harness/tool_mapper.py.")