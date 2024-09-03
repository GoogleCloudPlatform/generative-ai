# Use Non-Vertex AI LLMs

AlloyDB Omni supports registering non-vertex AI models and invoking predictions with [Model endpoint management](https://cloud.google.com/alloydb/docs/ai/model-endpoint-overview) in AlloyDB. Follow the steps below to use your preferred model for embeddings and text completion.

## Deploy AlloyDB Omni

This walkthrough uses model endpoint management capabilities in AlloyDB Omni. Follow the steps outlines in [alloydb-omni.md](./alloydb-omni.md) to replace hosted AlloyDB with AlloyDB Omni before proceeding to the next steps. 

## Secrets Manager

Create a secret and add permissions for the AlloyDB Omni service account to access Secrets Manager. This is required to securely store the API key(s) for your custom model(s). Update SERVICE_ACCOUNT_ID below with your service account ID for AlloyDB Omni.

1. Replace `API_KEY` below with the API key required for your local model, and run the command from Cloud Shell. 

    ```bash
    echo -n "API_KEY" | gcloud secrets create local-model-key \
        --replication-policy="automatic" \
        --data-file=-
    ```

1. Replace `SERVICE_ACCOUNT_ID` with your AlloyDB Omni service account and run the command from Cloud Shell.

    ```bash
    gcloud secrets add-iam-policy-binding 'local-model-key' \
        --member="serviceAccount:SERVICE_ACCOUNT_ID" \
        --role="roles/secretmanager.secretAccessor"
    ```

## Deploy Local Models

To use AlloyDB Omni's Model Endpoint Management feature with a custom model, you will need an endpoint for embeddings and text completion. For this walkthrough, we have provided examples for each model. You can use these models, or any other model with a compatible endpoint.

1. Deploy a local embeddings model using the examples provided in [this GitHub repo](https://github.com/llm-on-gke/sentence_transformers_serving).

1. Deploy a local text completion model using the examples provided in [this GitHub repo](https://github.com/IshmeetMehta/llm-on-gke).

## Register Local Models

Use pgAdmin to connect to the `ragdemos` database in your new AlloyDB Omni cluster and run the commands below one at a time to register local models for use with AlloyDB Omni.

1. Enable or the google_ml extension if not already installed.

    ```sql
    -- Create the extension
    CREATE EXTENSION google_ml_integration VERSION '1.3';
    
    -- Or update the extension if it already exists
    ALTER EXTENSION google_ml_integration UPDATE TO '1.3'
    ```

1. Enable model endpoint support.

    ```sql
    ALTER SYSTEM SET google_ml_integration.enable_model_support=on;
    ```

1. Reload the config.

    ```sql
    SELECT pg_reload_conf();
    ```

1. Register the Vertex AI embedding model for backward compatibility.

    ```sql
    CALL google_ml.create_model (
        model_id => 'textembedding-gecko@003',
        model_provider => 'google',
        model_qualified_name => 'textembedding-gecko@003',
        model_type => 'text_embedding',
        model_auth_type => 'alloydb_service_agent_iam'
    );
    ```

1. Register the Secrets Manager key you created earlier in AlloyDB Omni. Replace `PROJECT_NUMBER` with your project number before running the command.

    ```sql
    -- Create the api key (NOTE: This is required even if the API doesn't require a key - you at least need a placeholder.)

    CALL google_ml.create_sm_secret(
        secret_id => 'local-model-key',
        secret_path => 'projects/PROJECT_NUMBER/secrets/local-model-key/versions/1');
    ```

### Register a Local Embeddings Model

Use pgAdmin to run the commands below against the `ragdemos` database to register a local embeddings model for use with AlloyDB Omni. In this example, we use the gte-large-en-v1.5 model from [Hugging Face](https://huggingface.co/Alibaba-NLP/gte-large-en-v1.5)

1. Define an input transform function for the model.

    ```sql
    CREATE OR REPLACE FUNCTION gte_text_embedding_input_transform(
        model_id character varying,
        input_text text)
        RETURNS json
        LANGUAGE 'plpgsql'
        COST 100
        VOLATILE PARALLEL UNSAFE
    AS $BODY$
    #variable_conflict use_variable
    DECLARE
    transformed_input JSON;
    BEGIN
    CALL google_ml.check_model_support();
    SELECT json_build_object('inputs', json_build_array(input_text))::JSON INTO transformed_input;
    RETURN transformed_input;
    END;
    $BODY$;

    ALTER FUNCTION gte_text_embedding_input_transform(character varying, text)
    OWNER TO postgres;
    ```

1. Define an output transform function for the model.

    ```sql
    CREATE OR REPLACE FUNCTION gte_text_embedding_output_transform(
        model_id character varying,
        response_json json)
        RETURNS real[]
        LANGUAGE 'plpgsql'
        COST 100
        VOLATILE PARALLEL UNSAFE
    AS $BODY$
    DECLARE
    transformed_output REAL[];
    BEGIN
    CALL google_ml.check_model_support();
    SELECT ARRAY(SELECT json_array_elements_text(response_json->0))::REAL[] INTO transformed_output;
    RETURN transformed_output;
    END;
    $BODY$;

    ALTER FUNCTION gte_text_embedding_output_transform(character varying, json)
        OWNER TO postgres;
    ```

1. Replace `URL:PORT` in the model request URL below to match your embeddings endpoint before running the following command.

    ```sql
    CALL
    google_ml.create_model (
        model_id => 'textembedding-gte-large',
        model_request_url => 'http://URL:PORT/embed',
        model_provider => 'custom',
        model_qualified_name => 'Alibaba-NLP/gte-large-en-v1.5',
        model_type => 'text_embedding',
        model_auth_type => 'secret_manager',
        model_auth_id => 'local-model-key',
        model_in_transform_fn => 'gte_text_embedding_input_transform',
        model_out_transform_fn => 'gte_text_embedding_output_transform'
    );

1. Run a test query to ensure the new model is working as expected.

    ```sql
    SELECT google_ml.embedding('textembedding-gte-large', 'Test embeddings string')::vector
    ```

You can now use your custom embeddings model to generate embeddings directly in your database. 

### Register a Local Text Completion Model

Use pgAdmin to run the commands below against the `ragdemos` database to register a local text completion model for use with AlloyDB Omni. In this example, we use the Llama-2-70b-hf model from [Hugging Face](https://huggingface.co/meta-llama/Llama-2-70b-hf).

1. Replace `URL:PORT` with your model endpoint details before running the command below to register the local text completion model.

    ```sql
    CALL google_ml.create_model (
        model_id => 'llama2-70B',
        model_request_url => 'http://URL:PORT/generate',
        model_provider => 'custom',
        model_qualified_name => 'llama2-70B',
        model_type => 'generic',
        model_auth_type => 'secret_manager',
        model_auth_id => 'local-model-key'
    );

1. Run a test query to make sure the model works as expected.

    ```sql
    SELECT google_ml.predict_row('llama2-70B', '{    
        "prompt": "How far away is Mars from Earth?",
        "max_tokens": 128, 
        "top_p": 0.9,
        "temperature": 0.7
    }')
    ```

1. You can also format the response using JSON operators and the split_text() function to isolate just the response from the payload.

    ```sql
    SELECT split_part((google_ml.predict_row('llama2-70B', '{    
        "prompt": "How far is Mars from Earth?",
        "max_tokens": 128, 
        "top_p": 0.9,
        "temperature": 0.7
        }') -> 'predictions' ->> 0), E'Output:\n', 2)
    ```

### Create the llm_local() Function

Use pgAdmin to run the commands below against the `ragdemos` database to create the llm_local() function.

1. Copy and paste the function code from [llm_local.sql](../database-files/llm_local.sql) into a pgAdmin query window and run the query to create the function.

1. Run the test query below to make sure the function is working as expected.

    ```sql
    SELECT llm_prompt, llm_response
    FROM llm_local(
        prompt => 'How far is it to the moon?'
        );
    ```

## Generate Local Model Embeddings

Use pgAdmin to run the commands below against the `ragdemos` database to generate embeddings with your new local model.

> NOTE: Generating embeddings for the GenWealth test data requires an individual inference for each of the 2,000 bio fields in the user_profiles table, each of the 8,541 overview fields in the investments table, and each of the 8,541 analysis fields the investments table, totalling 19,082 total inferences. The time it takes to run this many inferences depends largely on the performance of your local embeddings model, but it can take several hours for the initial embedding process. The code uses triggers to keep the embeddings up to date as you change data, so you only incur this cold start penalty once.

1. Update the postgres user so that the initial embeddings queries don't time out. 

    ```sql
    ALTER USER postgres SET statement_timeout=0
    ```

1. Add local embeddings columns to the investments table and the user_profiles table. 

    > NOTE: We use 1024 vector dimensions here to match the embeddings model we use in this example. You may need to adjust this depending on how many dimensions the embeddings model you chose outputs.

    ```sql
    ALTER TABLE investments
    ADD COLUMN overview_embedding_local VECTOR(1024), 
    ADD COLUMN analysis_embedding_local VECTOR(1024);

    ALTER TABLE user_profiles
    ADD COLUMN bio_embedding_local VECTOR(1024);
    ```

1. Add triggers to keep embeddings up to date as data changes.

    ```sql
    CREATE OR REPLACE FUNCTION update_overview_embedding_local() RETURNS trigger AS $$
    BEGIN
      NEW.overview_embedding_local := google_ml.embedding('textembedding-gte-large', NEW.overview)::vector;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE TRIGGER overview_update_trigger_local
    BEFORE INSERT OR UPDATE OF overview ON investments
    FOR EACH ROW
    EXECUTE PROCEDURE update_overview_embedding_local();
    
    CREATE OR REPLACE FUNCTION update_analysis_embedding_local() RETURNS trigger AS $$
    BEGIN
      NEW.analysis_embedding_local := google_ml.embedding('textembedding-gte-large', NEW.analysis)::vector;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE TRIGGER analysis_update_trigger_local
    BEFORE INSERT OR UPDATE OF analysis ON investments
    FOR EACH ROW
    EXECUTE PROCEDURE update_analysis_embedding_local();
    ```

1. Create vector indexes to improve vector search performance.

    ```sql
    DROP INDEX IF EXISTS idx_hnsw_co_investments_overview_embedding_local;
    CREATE INDEX idx_hnsw_co_investments_overview_embedding_local
    ON investments USING hnsw (overview_embedding_local vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    DROP INDEX IF EXISTS idx_hnsw_co_investments_analysis_embedding_local;
    CREATE INDEX idx_hnsw_co_investments_analysis_embedding_local
    ON investments USING hnsw (analysis_embedding_local vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    DROP INDEX IF EXISTS idx_user_profiles_bio_embedding_local;
    CREATE INDEX idx_user_profiles_bio_embedding_local
    ON user_profiles USING hnsw (bio_embedding_local vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    ```

1. Generate local embeddings for the analysis and overview columns in the investments table.

    > NOTE: This step may take several hours depending on the performance of your embedding model.

    ```sql
    UPDATE investments 
        SET overview_embedding_local = google_ml.embedding('textembedding-gte-large', overview)::vector,
            analysis_embedding_local = google_ml.embedding('textembedding-gte-large', analysis)::vector
    ```

1. Generate local embeddings for the bio columns in the user_profiles table. You can open a second query window to kick this off in parallel while the step above runs if desired.

    ```sql
    UPDATE user_profiles
    SET bio_embedding_local = google_ml.embedding('textembedding-gte-large', bio)::vector
    WHERE bio_embedding_local IS NULL
    ```

1. If your pgAdmin session gets disconnected, your query should still be running in the background. Use the query below to check whether the queries are still running.

    ```sql
    SELECT datname, pid, state, query, age(clock_timestamp(), query_start) AS age 
    FROM pg_stat_activity
    WHERE state <> 'idle' 
        AND query NOT LIKE '% FROM pg_stat_activity %' 
    ORDER BY age;
    ```

1. Run test queries to make sure everything is working as expected.

    ```sql
    -- Test query for investments table
    SELECT ticker, etf, rating, analysis,
    analysis_embedding_local <=> google_ml.embedding('textembedding-gte-large', 'high inflation, hedge')::vector AS distance
    FROM investments
    ORDER BY distance
    LIMIT 5;

    -- Test query for user_profiles table
    SELECT id, first_name, last_name, email, age, risk_profile, bio,
    bio_embedding_local <=> google_ml.embedding('textembedding-gte-large', 'young aggressive investor')::vector AS distance
    FROM user_profiles WHERE risk_profile = 'high' AND age >= 18 AND age <= 55 ORDER BY distance LIMIT 50;
    ```
