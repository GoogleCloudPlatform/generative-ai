"""Configuration variables for the fashion trends prediction app."""

# pylint: disable=C0301
# pylint: disable=E0401

from typing_extensions import TypedDict

Config = TypedDict(
    "Config",
    {
        "PROJECT_ID": str,
        "LOCATION": str,
        "parameters": dict,
        "username": str,
        "password": str,
        "Images": dict,
        "Data": dict,
        "fewshot_images": dict,
        "countryList": list,
        "links": dict,
        "postid": int,
        "mode": int,
    },
)

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
        "logo": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/logo.png",  # noqa
        "trend": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/trend-page-img.avif",  # noqa
        "chat": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/chat.png",
        "imagen": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/canvas.png",
        "slide1": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/slide1.svg",
        "slide2": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/slide2.svg",
        "additional_tools": "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/images/additional_tools.svg",
    },
    "Data": {
        "current_data": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data/instagram_data.json",
        "chunks_local": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data/chunks_local.json",
        "chunks_prod": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data/chunks_prod.json",
        "vectorstore_local": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data/vectorstore_local.pkl",
        "vectorstore_prod": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data/vectorstore_prod.pkl",
    },
    "fewshot_images": {
        "image1": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data_prep/gemini_fewshot_images/image_1.jpg",
        "image2": "gs://github-repo/generative-ai/sample-apps/fashion-trends-prediction/app/data_prep/gemini_fewshot_images/image_2.jpg",
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
