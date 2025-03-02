#### Prerequisites
- Salesforce Connector Enabled datastore in Vertex AI Agent Builder
- Google Workforce Identity Federation with Salesforce as OIDC provider. Ensure in Salesforce OAuth application ```Configure ID Token``` and ```Include Standard Claims``` is checked
#### This code implements a complete OAuth 2.0 flow with PKCE to authenticate a user with Salesforce, exchange the Salesforce ID token for a Google Cloud access token via Workforce Identity Federation, and then uses that Google Cloud token to make a request to the Discovery Engine API, and prints the results.
