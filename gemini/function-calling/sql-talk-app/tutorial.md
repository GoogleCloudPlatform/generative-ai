# SQL Talk App - Cloud Shell Tutorial

## Running the SQL Talk app

This app demonstrates the power of Gemini's function calling capabilities,
enabling users to query and understand their BigQuery databases using natural
language. Forget complex SQL syntax – interact with your data conversationally.

Use the steps in this tutorial to run your own copy of the SQL Talk app using
Cloud Shell in your own Google Cloud project.

## Run the setup script

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

Then refresh the web app, and you should see the new title in place.

### Extending the app

Consider adding and modifying the available tools to perform:

- Data visualization: Create charts/graphs to summarize the findings
- Other database integrations: Support for PostgreSQL, MySQL, etc.
- APIs: Connect to weather APIs, translation services, and more.

## Cleanup

When you are done

- Delete the sample dataset in BigQuery
- Delete the data transfer job in BigQuery
- Disable the Vertex AI and BigQuery APIs

## Conclusion

Done!
