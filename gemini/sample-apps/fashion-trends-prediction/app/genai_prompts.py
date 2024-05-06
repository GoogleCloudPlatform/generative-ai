"""Module for prompts to be given to Gemini for generation."""

# pylint: disable=C0301


def fashion_bot_context(country: str, category: str, data: dict) -> str:
    """Generates a context for the fashion bot based on the given country and category.

    Args:
        country (str): The country for which to generate the context.
        category (str): The category of outfit for which to generate the context.
        data (dict): The data to use to generate the context.

    Returns:
        str: The generated context.
    """

    context = f"""You are a fashion expert in {category}. Answer fashion related queries solely based on the data provided.

    Important points -
    - The data provided represents what popular influencers are wearing nowadays
    - If user asks about something that is not present in the data, answer that it is not trending in fashion
    - Popularity of an item is proportional to its counts in the data
    - Counts of the item includes the frequency of semantically similar items
    - Don't mention counts with answer
    - If item is not in data provided, it is not fashionable.

    {category.capitalize()} data - """

    outfits_list = []
    if country in data and category in data[country]:
        for outfit in data[country][category]:
            if isinstance(outfit, str):
                outfits_list.append(outfit)
            if len(outfits_list) > 3000:
                break

    context += ", ".join(outfits_list)
    return context


FASHION_BOT_IMG_GEN_INTENT = "{text}, what does the user want to generate image of based on current chat history? Strictly give the name of the outfit only."


IMAGE_PROMPT = """

You are a fashion designer at a fast fashion retailer and your goal is to visualize different draft styles for a given outfit.

Instructions:
Suggest a prompt for generating a trendy image for the following outfit.

Rules:
- The prompt should use a suitable background that goes well with the outfit.
- The generated images should look natural.
- The focus should be on the outfit.


Outfit: {outfit}

"""


TRENDS_PROMPT = """

You are supposed to summarize trends in the data given.
- Iterate through the data entry by entry.
- Look at each entry carefully and do not overcount or undercount.
- The output should be strictly in a json format.
- The output should be within json curly braces with no extra characters before or after.

Few examples:

###################
Input:

You have the following dress data -

['black see-through maxi dress', 'white off-the-shoulder bubble dress', 'black sequin one-shoulder dress', 'black long-sleeved mini dress', 'black dress with a plunging neckline', 'black bodycon dress with a slit', 'red sparkly strapless dress', 'white one-shoulder maxi dress', 'black strapless dress', 'brown leather wrap dress', 'red turtleneck dress with a high slit', 'black dress with fur trim', 'black mini dress', 'sheer white maxi dress with ruching and a thigh-high slit', 'black halter dress', 'black dress with a plunging neckline', 'black one-shoulder dress', 'black dress with a tulle skirt', 'black mini dress', 'asymmetrical pink mini dress', 'red strapless ball gown with a black and green striped bandeau top', 'black dress', 'red off-the-shoulder dress', 'black off-the-shoulder dress', 'silver sequin dress']

First think of the different aspects/features in a dress. Eg. color, print, etc.

I want to know the maximum occurring values for each aspect. So, for each aspect, summarize the above data and list at most 5 values with counts in descending order of counts in json format.

Output:

{{
        "Color": {{
            "Black": 16,
            "Red": 4,
            "White": 3,
            "Brown": 1,
            "Pink": 1
        }},


        "Length": {{
            "mini": 4,
            "maxi": 3
        }},


        "Sleeve Length": {{
            "off-the-shoulder": 3,
            "strapless": 3,
            "one-shoulder": 3,
            "long-sleeved": 1
        }},


        "Neckline": {{
            "off-the-shoulder": 3,
            "strapless": 3,
            "one-shoulder": 3,
            "plunging": 2,
            "halter": 1
        }},


        "Material": {{
            "sequin": 2,
            "sheer": 2,
            "leather": 1,
            "fur": 1
        }},


        "Style": {{
            "bodycon": 1,
            "ball gown": 1,
            "wrap": 1,
            "asymmetrical": 1,
            "see-through": 1
        }},


        "Pattern": {{
            "Solid": 19,
            "Striped": 1
        }}
}}

###################
Input:

You have the following pants data -

['black wide-legged pants', 'black pants', 'plaid pants', 'olive green pleated pants', 'red latex pants', 'black pants', 'black pants', 'black pants', 'white sweatpants', 'black pants with silver studs', 'blue denim pants with crystal embellishment', 'black baggy pants', 'red sweatpants', 'black pants', 'black pants', 'black pants', 'black pants', 'black pants', 'grey sweatpants', 'faded blue low-waisted baggy jeans', 'white pants', 'black ski pants', 'brown flare pants', 'black leather pants with knee pads', 'light blue jeans with stars']

First think of the different aspects/features in a pants. Eg. color, print, etc.

I want to know the maximum occurring values for each aspect. So, for each aspect, summarize the above data and list at most 5 values with counts in descending order of counts in json format.

Output:

{{
        "Color": {{
            "Black": 14,
            "Blue": 3,
            "White": 2,
            "Red": 2,
            "Grey": 1
        }},


        "Fit": {{
            "sweatpants": 3,
            "baggy": 2,
            "wide-legged": 1,
            "low-waisted": 1
        }},


        "Material": {{
            "denim": 1,
            "latex": 1,
            "leather": 1,
            "plaid": 1
        }},


        "Embellishment": {{
            "studs": 1,
            "crystal": 1,
            "stars": 1
        }}
}}


###################
Input:

You have the following {category} data -

{data}

First think of the different aspects/features in a {category}. Eg. color, print, etc.

I want to know the maximum occurring values for each aspect. So, for each aspect, summarize the above data and list at most 5 values with counts in descending order of counts in json format.

Output:


"""


ARTICLES_PROMPT = """You are a fashion journalist and want to know whether an article is talking about a given fashion clothing item. Answer this by searching for the presence of the item or a similar item in the text. The first word of the output should be Yes/No.

Examples:

input_text = Is the following article related to White tie dye dress - Tie-dye, known for its vibrant and carefree nature, has evolved through different eras, from the 60s hippie movement to the 90s stoner culture, and recently, the \\\"scumbro\\\" style. Alia Bhatt showcased a tie-dye lounge set, representing the hedonistic and relaxed spirit of the trend. While it may not dominate red carpets as before, tie-dye is making a comeback in subtle ways, such as Bhatt\\\'s outfit, symbolizing fun and carefree vibes.

output_text = Yes, since the article contains the main component of the query item that is tie dye.

#####

input_text = Is the following article related to Off the shoulder knit brown dress - While some Bollywood celebrities are attending Diwali events, Shanaya Kapoor is vacationing in the Maldives. She showcased several stylish outfits during her trip, including a cobalt blue bikini top with a checkered skirt, a ruffled bralette and skirt set, a bustier with a chunky knit skirt, and a crochet dress. Kapoor\\\'s vacation style is reminiscent of the knitwear and crochet trend seen in recent years, popularized by celebrities like Kim Kardashian and Kylie Jenner.

output_text = Yes, since the article mentions knitwear which is the main component of the query item.

#####

input_text = Is the following article related to white cotton jacket - It was a big weekend for Kylie Jenner and Timothée Chalamet. The actor hosted Saturday Night Live last night in New York City, where he was joined by the musical guest Boygenius. And while the star nailed his comedic sketches on-screen—did you catch him as a Troye Sivan sleep demon?—it was the show’s after-party that we’re particularly intrigued by. Stepping out with the rest of the SNL cast, Chalamet was joined by girlfriend Kylie Jenner—and they both embraced polar-opposite date night style for the affair, no less.Photo: Getty ImagesWhile Jenner and Chalamet have kept things coy and have rarely stepped out in public, the couple hit the town together last night, and they couldn’t be dressed more differently. Jenner continued her winning style streak of sleek, all-black looks: She wore an off-the-shoulder mini dress with shiny leggings and black strappy pumps. Chalamet, meanwhile, went a sportier and more colorful route: He sported a purple zip-up jacket with a colour-blocked hoodie and grey jeans.Photo: Getty ImagesTheir juxtaposing fashion vibe is something we’ve seen other A-list couples, like the Biebers, pull off. Who says couples have to match? As they’ve proven with their clashing outfits, individuality rules.This article first appeared on vogue.comTimothée Chalamet and Zendaya illustrate two different ways to pull off a vestKylie Jenner picks up her first fashion designer plaudit with Timothée in towThe pantless trend really is happening—and Kylie Jenner is hopping on the trend.

output_text = No, this article is not talking about white cotton jacket. At the maximum, the article mentions jacket but that is a very generic item and should not be given that much importance.

#####

input_text = Is the following article related to {outfit} - {article} Respond in Yes or No.

output_text ="""
