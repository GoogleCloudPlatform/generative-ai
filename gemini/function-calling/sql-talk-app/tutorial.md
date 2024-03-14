# SQL Talk App - Cloud Shell Tutorial

## Running the SQL Talk app

### Run the setup script

Run the following command in the Cloud Shell:

```
bash setup.sh
```

This script will:

- Enable the Vertex AI and BigQuery APIs
- Install Python and packages
- Start the SQL Talk app

### Access the app

In the Cloud Shell toolbar, click the `Web Preview` icon, then select the option
to `Preview on port 8080`. You should see a running version of the app and
interact with it as usual.

## Make a change

Make a simple change to the app such as changing the app title from:

```python
st.title("SQL Talk with BigQuery")
```

to:

```python
st.title("Hello from SQL Talk with BigQuery")
```

### Explore another dataset

Try rewriting the function definitions and application code to try new things!

Try changing the `BIGQUERY_DATASET_ID` to another dataset in the BigQuery Public
Datasets such as `stackoverflow` or `github_repos`.

### Extending the app

Consider adding and modifying the available tools to perform:

- Data visualization: Create charts/graphs to summarize the findings
- Other database integrations: Support for PostgreSQL, MySQL, etc.
- APIs: Connect to weather APIs, translation services, and more.

## Conclusion

Done!
