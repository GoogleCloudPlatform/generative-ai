image_prompt = """

You are a fashion designer at a fast fashion retailer and your goal is to visualize different draft styles for a given outfit.

Instructions:
Suggest a prompt for generating a trendy image for the following outfit.

Rules:
- The prompt should use a suitable background that goes well with the outfit.
- The generated images should look natural.
- The focus should be on the outfit.


Outfit: {outfit}

"""


trends_prompt = """

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


qList = [
    "Is there a person in the photo (yes/no)?",
    "What is the name of each part of the outfit?",
    "What is the type of sleeves?",
    "What is the type of neckline or collar?",
    "What are the jewellery items worn?",
]


qList2 = [
    "What is the type of x?",
    "What is the color of x?",
    "What is the material of x?",
]
