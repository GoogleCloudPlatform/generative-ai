from google.cloud.aiplatform import Model

GOOGLE_AI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.0-pro",

]

class ModelService:

    def get_all(self):
        custom_models = Model.list()
        return [
            {
                "name": "Gemini",
                "models": GOOGLE_AI_MODELS,
            },
            {
                "name": "Custom",
                "models": [cm.display_name for cm in custom_models],
            }
        ]