from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("cocktaildb")

# Constants
API_BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1/"


# --- Helper Functions ---
async def make_cocktaildb_request(
    endpoint: str, params: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """Makes a request to TheCocktailDB API and returns the JSON response."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()
            # The API returns null string instead of null JSON for no results
            if isinstance(data, str) and data.lower() == "null":
                return None
            # Handle cases where the primary key (drinks/ingredients) might be null
            if data and (
                data.get("drinks") is None and data.get("ingredients") is None
            ):
                # Check if it's a known 'no result' structure or genuinely empty
                if "drinks" in data or "ingredients" in data:
                    return None  # Explicitly no results found based on API structure
            return data
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        return None
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}: {e}")
        return None


def format_cocktail_summary(drink: Dict[str, Any]) -> str:
    """Formats a cocktail dictionary into a readable summary string."""
    return (
        f"ID: {drink.get('idDrink', 'N/A')}\n"
        f"Name: {drink.get('strDrink', 'N/A')}\n"
        f"Category: {drink.get('strCategory', 'N/A')}\n"
        f"Glass: {drink.get('strGlass', 'N/A')}\n"
        f"Alcoholic: {drink.get('strAlcoholic', 'N/A')}\n"
        f"Instructions: {drink.get('strInstructions', 'N/A')[:150]}...\n"
        f"Thumbnail: {drink.get('strDrinkThumb', 'N/A')}"
    )


def format_cocktail_details(drink: Dict[str, Any]) -> str:
    """Formats a cocktail dictionary into a detailed readable string."""
    details = [
        f"ID: {drink.get('idDrink', 'N/A')}",
        f"Name: {drink.get('strDrink', 'N/A')}",
        f"Alternate Name: {drink.get('strDrinkAlternate', 'None')}",
        f"Tags: {drink.get('strTags', 'None')}",
        f"Category: {drink.get('strCategory', 'N/A')}",
        f"IBA Category: {drink.get('strIBA', 'None')}",
        f"Alcoholic: {drink.get('strAlcoholic', 'N/A')}",
        f"Glass: {drink.get('strGlass', 'N/A')}",
        f"Instructions: {drink.get('strInstructions', 'N/A')}",
    ]
    ingredients = []
    for i in range(1, 16):
        ingredient = drink.get(f"strIngredient{i}")
        measure = drink.get(f"strMeasure{i}")
        if ingredient:
            ingredients.append(
                f"- {measure.strip() if measure else ''} {ingredient.strip()}".strip()
            )
    if ingredients:
        details.append("\nIngredients:")
        details.extend(ingredients)

    details.append(f"\nImage URL: {drink.get('strDrinkThumb', 'N/A')}")
    details.append(f"Last Modified: {drink.get('dateModified', 'N/A')}")

    return "\n".join(details)


def format_ingredient(ingredient: Dict[str, Any]) -> str:
    """Formats an ingredient dictionary into a readable string."""
    desc = ingredient.get("strDescription", "No description available.")
    return (
        f"ID: {ingredient.get('idIngredient', 'N/A')}\n"
        f"Name: {ingredient.get('strIngredient', 'N/A')}\n"
        f"Type: {ingredient.get('strType', 'N/A')}\n"
        f"Alcoholic: {ingredient.get('strAlcohol', 'Unknown')}\n"
        f"ABV: {ingredient.get('strABV', 'N/A')}\n"
        f"Description: {desc[:300] + '...' if desc and len(desc) > 300 else desc}"
    )


# --- MCP Tools ---


@mcp.tool()
async def search_cocktail_by_name(name: str) -> str:
    """Searches for cocktails by name.

    Args:
        name: The name of the cocktail to search for (e.g., margarita).
    """
    data = await make_cocktaildb_request("search.php", params={"s": name})
    if data and data.get("drinks"):
        drinks = data["drinks"]
        response_lines = ["Found cocktails:"]
        response_lines.extend([format_cocktail_summary(drink) for drink in drinks])
        return "\n---\n".join(response_lines)
    return "No cocktails found with that name."


@mcp.tool()
async def list_cocktails_by_first_letter(letter: str) -> str:
    """Lists all cocktails starting with a specific letter.

    Args:
        letter: The first letter to search cocktails by (must be a single character).
    """
    if len(letter) != 1 or not letter.isalpha():
        return "Invalid input: Please provide a single letter."
    data = await make_cocktaildb_request("search.php", params={"f": letter.lower()})
    if data and data.get("drinks"):
        drinks = data["drinks"]
        response_lines = [f"Cocktails starting with '{letter.upper()}':"]
        response_lines.extend([format_cocktail_summary(drink) for drink in drinks])
        return "\n---\n".join(response_lines)
    return f"No cocktails found starting with the letter '{letter.upper()}'"


@mcp.tool()
async def search_ingredient_by_name(name: str) -> str:
    """Searches for an ingredient by its name.

    Args:
        name: The name of the ingredient to search for (e.g., vodka).
    """
    data = await make_cocktaildb_request("search.php", params={"i": name})
    if data and data.get("ingredients"):
        ingredient = data["ingredients"][0]  # API returns a list with one item
        return format_ingredient(ingredient)
    return "No ingredient found with that name."


@mcp.tool()
async def list_random_cocktails() -> str:
    """Looks up a single random cocktail."""
    data = await make_cocktaildb_request("random.php")
    if data and data.get("drinks"):
        drink = data["drinks"][0]
        return format_cocktail_details(drink)
    return "Could not fetch a random cocktail."


@mcp.tool()
async def lookup_cocktail_details_by_id(cocktail_id: str) -> str:
    """Looks up the full details of a specific cocktail by its ID.

    Args:
        cocktail_id: The unique ID of the cocktail.
    """
    # Validate if cocktail_id is numeric
    if not cocktail_id.isdigit():
        return "Invalid input: Cocktail ID must be a number."

    data = await make_cocktaildb_request("lookup.php", params={"i": cocktail_id})
    if data and data.get("drinks"):
        drink = data["drinks"][0]
        return format_cocktail_details(drink)
    return f"No cocktail found with ID {cocktail_id}."


# --- Run Server ---
if __name__ == "__main__":
    mcp.run(transport="stdio")
