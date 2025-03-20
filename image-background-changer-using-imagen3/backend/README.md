# QuickBot App Backend | image-background-changer-using-imagen3

[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)

QuickBot App is a set of templates that can be deployed out of the box into Cloud Run and work independently. Each one can be run independently connected to the user default google cloud auth credentials, and based on the complexity of each template, may require to deploy more or less resources into our Google Cloud Project. 
The architecture always follows the following structure: a folder for the frontend which consists in an Angular app, and a backend folder which consists of a FastAPI Python app.


## Setting up
### 1. Create virtualenv inside the backend folder and install dependencies
Create a virtual environment on the root of the application, activate it and install the requirements
```
# check if you are already in the env
pip -V

# if not then
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

> **IMPORTANT!** VS Code may not recognize your env, in that case type "ctrl + shift + P", then select "Python: Select Interpreter" and then select "Enter interpreter path..." and then select your .venv python interpreter, in this case .backend/.venv/bin/python


### 2. Setup gcloud credentials
```
gcloud auth list
gcloud config list

gcloud auth login
gcloud config set project <your project id> 
gcloud auth application-default set-quota-project <your project id>

gcloud auth list
gcloud config list
```

### 3. Add environment variables

#### If you have Mac or Windows (or if you are using zsh console on Linux)
```
. ./local.env
```

#### If you have Linux
Open the file .venv/bin/activate and paste the env variables from `.local.env` after the PATH export, like this:
```
...

_OLD_VIRTUAL_PATH="$PATH"
PATH="$VIRTUAL_ENV/bin:$PATH"
export PATH

# Quickbot env variables
export FRONTEND_URL=http://localhost:4200

...
```

Check that the env variables has been taken into account, running: 
```
env
```
You should see the new env variables set there


### 4. Run the application
Finally run using uvicorn
```
uvicorn main:app --reload --port 8080
```