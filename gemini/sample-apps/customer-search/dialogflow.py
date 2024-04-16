"""Creates Dialogflow CX Flows for CymBuddy Assistant."""

import json


def create_cymbuddy_df():
    """Adds Webhook URLS to the DialogFlow CX JSON template.

    Replaces webhook url placeholders in the DialogFlow CX JSON template
    with the URLs of the Cloud Functions deployed using Terraform.

    Input files (statically defined):
    - output_urls.txt: Contains Cloud Function URLs.
                       Generated after Terraform completes resource deployment.
    - CymBuddy.json: DialogFlow CX JSON template for CymBuddy assistant

    Output files:
    - CymBuddy_new.json: Created and saved in files/ folder locally by this program
    """
    with open("output_urls.txt", "r") as f:
        # read the text file into a list of lines
        lines = f.readlines()
    # create an empty dictionary
    file_dict = {}

    # loop through the lines in the text file
    for line in lines:
        # split the line on ":"
        key, value = line.split("=")
        # strip the whitespace
        key = key.strip()
        value = value.strip()
        # add the key, value pair to the dictionary
        file_dict[key] = value

    with open("files/CymBuddy.json", "r") as file:
        json_data = json.load(file)

    print("Type of JSON Object: ", type(json_data))

    for i in range(len(json_data["flow"]["fulfillments"])):
        if (
            json_data["flow"]["fulfillments"][i]["value"]["webhook"]["url"].split("/")[
                -1
            ]
            + "_url"
            in file_dict
        ):
            json_data["flow"]["fulfillments"][i]["value"]["webhook"]["url"] = file_dict[
                json_data["flow"]["fulfillments"][i]["value"]["webhook"]["url"].split(
                    "/"
                )[-1]
                + "_url"
            ]
        else:
            search_str = json_data["flow"]["fulfillments"][i]["value"]["webhook"][
                "url"
            ].split("/")[-1]
            search_str = search_str.replace("_", "-")
            if search_str + "_url" in file_dict:
                json_data["flow"]["fulfillments"][i]["value"]["webhook"][
                    "url"
                ] = file_dict[search_str + "_url"]
            else:
                print(search_str)

    for i in range(len(json_data["referencedFlows"][0]["fulfillments"])):
        if (
            json_data["referencedFlows"][0]["fulfillments"][i]["value"]["webhook"][
                "url"
            ].split("/")[-1]
            + "_url"
            in file_dict
        ):
            json_data["referencedFlows"][0]["fulfillments"][i]["value"]["webhook"][
                "url"
            ] = file_dict[
                json_data["referencedFlows"][0]["fulfillments"][i]["value"]["webhook"][
                    "url"
                ].split("/")[-1]
                + "_url"
            ]
        else:
            search_str = json_data["referencedFlows"][0]["fulfillments"][i]["value"][
                "webhook"
            ]["url"].split("/")[-1]
            search_str = search_str.replace("_", "-")
            if search_str + "_url" in file_dict:
                json_data["referencedFlows"][0]["fulfillments"][i]["value"]["webhook"][
                    "url"
                ] = file_dict[search_str + "_url"]
            else:
                print(search_str)

    with open("files/CymBuddy_new.json", "w") as new_df:
        json.dump(json_data, new_df)


if __name__ == "__main__":
    create_cymbuddy_df()
