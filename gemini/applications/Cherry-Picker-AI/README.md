# CherryPicker.AI 🍒

![Image of the Logo for the CherryPicker.AI Application: Perry the Cherry](https://media.licdn.com/dms/image/v2/D5622AQG9ymz2uaew4g/feedshare-shrink_800/feedshare-shrink_800/0/1730653525795?e=1735776000&v=beta&t=-ZTrGHhoqK1XDOTNJWcDrHHQMuVaOxaSWQIotsr7pBc)

## Description

This app is a machine learning tool that can analyze images of produce and provide feedback on its quality. It also will generate a personalized advertisements for poorly rated produce based on sponsor grocery stores (based on the type of produce they are looking for).

* Here is a link to a video demo of the application. (Send to Github Generative AI Team to create shareable link)
* This application was originally demo'ed on [November 5th, 2024](https://www.youtube.com/live/MJBqVVkRbNM?si=DdZK_Ry3cCj1p1-T).

The app was built in 24 hours using a variety of technologies, including:

* Project IDX
* Google Gemini
* Python
* Flask
* Vuetify
* ChromaDB
* Vertex AI


## Features

* Analyzes images of produce and provides feedback on its quality
* Generates personalized advertisements for grocery stores
* Built using Google Gemini and other cutting-edge technologies
* Easy to use and deploy


## Usage

To use the app, simply upload an image of produce. The app will then analyze the image and provide feedback on the quality of the produce. The app will also generate a personalized advertisement for a grocery store 'near you' that sells the type of produce you are looking for.

## Run and modify the app in Cloud Shell Editor

* After you've tried out the live demo app, you can also run your own version of the SQL Talk app and make changes to the live app using the Cloud Shell Editor in your own Google Cloud project.

* Open this repository and the sample app in the Cloud Shell Editor, then follow the steps displayed in the tutorial in the sidebar.

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fzthor5%2Fcherrypickerai.git&cloudshell_git_branch=main&cloudshell_tutorial=tutorial.md)

## Contributing

* We welcome contributions from the community. Feel free to make your versions checking the quality of flowers, or any ideas you can think of!
* Please feel free to submit pull requests or file issues on GitHub.

## Addition features to be added
Not all features were implemented as desired within the 24 hour time limit; Community PR's are welcomed to add implementations of features such as:

* Bounding Box Implementation with higher accuracy (Utilize a Vision ML model)
* ChromaDB to return the correct Weekly Flyer based on the selected context.
* Change Auth to not require user verification.
* Enable Imagen3 to send a custom image along with the personalized Advertisment to the frontend.
* Add Context Validation for ChromaDB
* And more features as desired!

## Backend

![Backend Architecture of user flow]()

## Contact

If you have any questions, please contact us at..
* cristianruiz@google.com
* zthor@google.com 
