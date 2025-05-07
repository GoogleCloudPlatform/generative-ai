# QuickBotApp website-search-using-agent-builder

## Setting up
### 1. Create virtualenv and install dependencies
Create a virtual environment on the root of the application, activate it and install the requirements
```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

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

### 3. Running the set up script

Ensure the necessary APIs are enabled for your project.
At a minimum, you will need: 
**BigQuery API**
**Discovery Engine API** (IAM roles to interact with Discovery Engine e.g.
"Discovery Engine Viewer" or "Discovery Engine Admin")
Then run

```
python3 setup.py
```

### 4. Add environment variables

#### If you have Mac or Windows
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

# QUICKBOT ENV VARIABLES
export FRONTEND_URL=http://localhost:4200
export BIG_QUERY_DATASET=eren

...
```

Check that the env variables has been taken into account, running: 
```
env
```
You should see the new env variables set there


### 5. Run the application
Finally run using uvicorn
```
uvicorn main:app --reload --port 8080
```