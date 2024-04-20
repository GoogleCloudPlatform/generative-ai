from typing_extensions import TypedDict

Config = TypedDict('Config', {"PROJECT_ID": str, "LOCATION": str, "parameters": dict, "username": str,
                   "password": str, "Images": dict, "Data": dict, "countryList": list, "links": dict, "postid": int, "mode": int})

config: Config = {
    # "PROJECT_ID": "<YOUR_GCP_PROJECT_ID>",
    "PROJECT_ID": "aurora-cohort-2",
    "LOCATION": "us-central1",
    "parameters": {
        "standard": {
            "max_output_tokens": 4096,
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
        },
        "final_prediction": {
            "max_output_tokens": 128,
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
        },
        "fashion_bot": {
            "max_output_tokens": 8192,
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 40,
        },
    },
    # The following is needed if you want to scrape your own data
    "username": "<YOUR_INSTAGRAM_USERNAME>",
    "password": "<YOUR_INSTAGRAM_PASSWORD>",
    "Images": {
        "logo": "images/logo.png",
        "home": "images/home.png",
        "trend": "images/trend-page-img.avif",
        "chat": "images/chat.png",
        "imagen": "images/canvas.png",
        "slide1": "images/slide1.svg",
        "slide2": "images/slide2.svg",
        "additional_tools": "images/additional_tools.svg",
    },
    "Data": {
        "current_data": "data/instagram_data.json",
    },
    "countryList": [
        "All countries",
        "Australia",
        "Canada",
        "India",
        "Indonesia",
        "Japan",
        "Malaysia",
        "Philippines",
        "Singapore",
        "United States",
    ],
    "links": {
        "graphql": "https://www.instagram.com/graphql/query/",
        "instalogin": "https://i.instagram.com/api/v1/accounts/login/",
    },
    "postid": 17888483320059182,  # id for posts on instagram
    "mode": 0,  # set 0 for LOCAL and 1 for PROD
}
