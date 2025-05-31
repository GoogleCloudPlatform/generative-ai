## Setting up

Create a virtual environment on the root of the application and activate it.

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

### Running the set up script

```
python3 setup.py
```

### Running the application on local
Create a virtual environment, activate it, install the requirements, set environmental variables from local.env and run the application

```
. ./local.env
uvicorn main:app --reload --port 8080
```