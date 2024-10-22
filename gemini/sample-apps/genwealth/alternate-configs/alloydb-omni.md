# Use AlloyDB Omni

[AlloyDB Omni](https://cloud.google.com/alloydb/omni?hl=en) is a downloadable edition of AlloyDB, designed to run anywhere — in your data center, on your laptop, at the edge, and in any cloud.

This document provides step-by-step instructions for replacing the fully-managed AlloyDB instance deployed with the GenWealth app with AlloyDB Omni running on [GKE](https://cloud.google.com/kubernetes-engine?hl=en).

## Deploy the GenWealth App

This guide assumes you have already deployed the GenWealth app as defined [here](../../README.md). Deploy the app into a new project before proceeding to the next step.

## Provision the GKE Cluster

1. Enable the Kubernetes Engine API

    ```bash
    gcloud services enable container.googleapis.com
    ```

1. Open Cloud Shell, and run the command below to provision a GKE cluster to host the AlloyDB Omni database.

    > NOTE: Ensure there are no organization policies preventing public IP or requiring shielded VMs before running the command below.

    ```bash
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    ZONE="us-central1-c"
    VPC="demo-vpc"

    gcloud container --project ${PROJECT_ID} clusters create genwealth-gke --zone ${ZONE} --no-enable-basic-auth --release-channel "regular" --machine-type "n2-standard-4" --image-type "COS_CONTAINERD" --disk-type "pd-ssd" --disk-size "100" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --num-nodes "1" --logging=SYSTEM,WORKLOAD --monitoring=SYSTEM --enable-ip-alias --network ${VPC} --subnetwork ${VPC} --no-enable-intra-node-visibility --security-posture=standard --workload-vulnerability-scanning=disabled --no-enable-master-authorized-networks --addons HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver --enable-autorepair --enable-managed-prometheus --enable-shielded-nodes --node-locations ${ZONE}

    ```

1. Connect Cloud Shell to the GKE cluster:

    ```bash
    sudo apt-get install kubectl
    sudo apt-get install google-cloud-cli-gke-gcloud-auth-plugin
    gcloud container clusters get-credentials genwealth-gke --zone=us-central1-c
    ```

1. Test kubectl to ensure you are connected to the cluster.

    ```bash
    kubectl config current-context
    kubectl get namespaces
    ```

## Setup Pre-requisites for AlloyDB AI

1. AlloyDB Omni uses service account authentication for Vertex AI. To use the AlloyDB Vertex AI integration you need to first create a service account.

    ```bash
    SA_NAME="alloydb-omni-sa"
    gcloud iam service-accounts create $SA_NAME \
        --description="Service account for AlloyDB Omni to access " \
        --display-name="AlloyDB Omni Vertex AI Service Account"
    ```

1. Grant Vertex AI access to the service account.

    ```bash
    gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/aiplatform.user"

1. Create a private public key pair and download the private key.

    > NOTE: Ensure you do not have any organizational policies preventing you from creating service account keys before running the command below.

    ```bash
    gcloud iam service-accounts keys create ~/private-key.json  --iam-account=$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com

    ```

1. Create a secret containing your Vertex AI Service Account json file. Here `vertex-ai-secret` is the name of the secret.

    ```bash
    kubectl create secret generic vertex-ai-secret --from-file=./private-key.json
    ```

## Install AlloyDB Omni on GKE

Execute the steps below to install AlloyDB Omni on the GKE cluster. See the [AlloyDB Omni documentation](https://cloud.google.com/alloydb/docs/omni/deploy-kubernetes) for more details.

1. Install the [cert-manager](https://cert-manager.io/docs/installation/) service.

    ```bash
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.5/cert-manager.yaml
    ```

1. Install [Helm](https://helm.sh/docs/intro/install/).

    ```bash
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
    ```

1. Download the AlloyDB Omni Operator

    ```bash
    export GCS_BUCKET=alloydb-omni-operator
    export HELM_PATH=$(gsutil cat gs://$GCS_BUCKET/latest)
    export OPERATOR_VERSION="${HELM_PATH%%/*}"
    gsutil cp -r gs://$GCS_BUCKET/$HELM_PATH ./
    ```

1. Install the AlloyDB Omni Operator

    ```bash
    helm install alloydbomni-operator alloydbomni-operator-${OPERATOR_VERSION}.tgz \
        --create-namespace \
        --namespace alloydb-omni-system \
        --atomic \
        --timeout 5m
    ```

1. Create an AlloyDB Omni Database cluster.

    > IMPORTANT: Change the value of `<ENCODED_PASSWORD>` below to a Base64-encoded password.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: v1
    kind: Secret
    metadata:
      name: db-pw-genwealth-cluster
    type: Opaque
    data:
      genwealth-cluster: "<ENCODED_PASSWORD>"
    ---
    apiVersion: alloydbomni.dbadmin.goog/v1
    kind: DBCluster
    metadata:
      name: genwealth-cluster
    spec:
      databaseVersion: "15.5.2"
      primarySpec:
        adminUser:
          passwordRef:
            name: db-pw-genwealth-cluster
        resources:
          cpu: 2
          memory: 8Gi
          disks:
          - name: DataDisk
            size: 50Gi
            storageClass: standard
        features: 
          googleMLExtension:
            config:
              vertexAIKeyRef: vertex-ai-secret
    EOF
    ```

1. Ensure the DBCluster is in the `Ready` state before proceeding to the next step (this can take a few minutes). Check cluster status using the following command.

    ```bash
    kubectl get dbclusters
    ```

1. Create an internal load balancer to access AlloyDB Omni from outside the cluster.

    ```bash
    kubectl apply -f - <<EOF
    apiVersion: v1
    kind: Service
    metadata:
      name: alloydb-svc
      annotations:
        networking.gke.io/load-balancer-type: "Internal"
    spec:
      type: LoadBalancer
      externalTrafficPolicy: Cluster
      selector:
        alloydbomni.internal.dbadmin.goog/dbcluster: genwealth-cluster
        alloydbomni.internal.dbadmin.goog/task-type: database
        egress.networking.gke.io/enabled: "true"
      ports:
      - name: db
        protocol: TCP
        port: 5432
        targetPort: 5432
    EOF
    ```

1. Wait for the load balancer to assign an external ip, then write it down (you will need it for the next step). Check status with the command below.

    ```bash
    kubectl get service alloydb-svc
    ```

2. Login to pgAdmin as described in the [backend demo walkthrough](../walkthroughs/backend-demo-walkthrough.md).

3. Create a new connection to AlloyDB Omni in pgAdmin using the external IP of the `alloydb-svc` load balancer created above. Use the `postgres` user and the password you defined in the kubernetes manifest earlier when you created the AlloyDB Omni cluster.

## Configure the Database

1. SSH from Cloud Shell to the pgadmin instance to run commands against the database.

    ```bash
    gcloud compute ssh pgadmin --tunnel-through-iap --zone=us-central1-a
    ```

1. Set database login variables.

    ```bash
    read -rp "Enter your AlloyDB Omni Internal LB IP: " OMNI_IP

    read -rsp "Enter your AlloyDB Omni Password: " OMNI_PW
    ```

1. Test the psql connection. This command should return the current time.

    ```bash
    sql="SELECT CURRENT_TIMESTAMP"
    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d postgres
    ```

1. Create the ragdemos database.

    ```bash
    sql="CREATE DATABASE ragdemos;"
    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d postgres
    ```

1. Install pgvector.

    ```bash
    sql=$( cat <<EOF
    CREATE EXTENSION IF NOT EXISTS google_ml_integration VERSION '1.3' CASCADE;
    GRANT EXECUTE ON FUNCTION embedding TO postgres;
    CREATE EXTENSION IF NOT EXISTS vector CASCADE;
    EOF
    )

    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos
    ```

1. Create tables and indexes.

    ```bash
    sql=$( cat <<EOF
    CREATE TABLE investments (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(255) NOT NULL UNIQUE,
    etf BOOLEAN,
    market VARCHAR(255),
    rating TEXT,
    overview TEXT,
    overview_embedding VECTOR (768),
    analysis TEXT,
    analysis_embedding VECTOR (768)
    );

    DROP INDEX IF EXISTS idx_hnsw_co_investments_overview_embedding;
    CREATE INDEX idx_hnsw_co_investments_overview_embedding
    ON investments USING hnsw (overview_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    DROP INDEX IF EXISTS idx_hnsw_co_investments_analysis_embedding;
    CREATE INDEX idx_hnsw_co_investments_analysis_embedding
    ON investments USING hnsw (analysis_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash CHAR(60) NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    age INT, 
    risk_profile TEXT,
    bio TEXT,
    bio_embedding VECTOR(768)
    );

    DROP INDEX IF EXISTS idx_user_profiles_bio_embedding;
    CREATE INDEX idx_user_profiles_bio_embedding
    ON user_profiles USING hnsw (bio_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    CREATE TABLE IF NOT EXISTS conversation_history (
        id SERIAL PRIMARY KEY,  
        user_id INTEGER, 
        user_prompt TEXT, 
    user_prompt_embedding VECTOR(768) GENERATED ALWAYS AS (google_ml.embedding('textembedding-gecko@003', user_prompt)::vector) STORED,
        ai_response TEXT,
    ai_response_embedding VECTOR(768) GENERATED ALWAYS AS (google_ml.embedding('textembedding-gecko@003', ai_response)::vector) STORED,
        datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
    );

    DROP INDEX IF EXISTS idx_hnsw_co_conversation_history_user_prompt_embedding;
    CREATE INDEX idx_hnsw_co_conversation_history_user_prompt_embedding
    ON conversation_history USING hnsw (user_prompt_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    DROP INDEX IF EXISTS idx_hnsw_co_conversation_history_ai_response_embedding;
    CREATE INDEX idx_hnsw_co_conversation_history_ai_response_embedding
    ON conversation_history USING hnsw (ai_response_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    DROP TABLE IF EXISTS public.langchain_vector_store;
    CREATE TABLE IF NOT EXISTS public.langchain_vector_store
    (
        langchain_id uuid NOT NULL,
        content text COLLATE pg_catalog."default" NOT NULL,
        embedding vector(768) NOT NULL,
        source character varying COLLATE pg_catalog."default",
        page integer,
        ticker character varying COLLATE pg_catalog."default",
        page_size integer,
        doc_ai_shard_count integer,
        doc_ai_shard_index integer,
        doc_ai_chunk_size integer,
        doc_ai_chunk_uri character varying COLLATE pg_catalog."default",
        page_chunk integer,
        chunk_size integer,
        langchain_metadata json,
        CONSTRAINT langchain_vector_store_pkey PRIMARY KEY (langchain_id)
    )

    TABLESPACE pg_default;

    ALTER TABLE IF EXISTS public.langchain_vector_store
        OWNER to postgres;

    DROP INDEX IF EXISTS public.idx_hnsw_co_langchain_vector_store_embedding;
    CREATE INDEX IF NOT EXISTS idx_hnsw_co_langchain_vector_store_embedding
        ON public.langchain_vector_store USING hnsw
        (embedding vector_cosine_ops)
        TABLESPACE pg_default;
    EOF
    )

    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos
    ```

1. Load database tables with demo data.

    ```bash
    echo "Downloading data"
    cd || echo "Could not cd into user profile root"
    mkdir -p /tmp/demo-data
    cd /tmp/demo-data || echo "Could not cd into user profile root"
    gsutil -m cp \
      "gs://pr-public-demo-data/genwealth-demo/investments" \
      "gs://pr-public-demo-data/genwealth-demo/user_profiles" \
      "gs://pr-public-demo-data/genwealth-demo/llm.sql" .
    
    sql=$( cat <<EOF
    \copy investments FROM '/tmp/demo-data/investments' WITH (FORMAT csv, DELIMITER '|', QUOTE "'", ESCAPE "'")
    EOF
    )

    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos

    sql=$( cat <<EOF
    \copy user_profiles FROM '/tmp/demo-data/user_profiles' WITH (FORMAT csv, DELIMITER '|', QUOTE "'", ESCAPE "'")
    EOF
    )

    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos

    ```

1. Create the llm() function

    ```bash
    PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos <llm.sql
    ```

1. Create embeddings triggers.

    ```bash
    sql=$( cat <<EOF
    CREATE OR REPLACE FUNCTION update_overview_embedding() RETURNS trigger AS \$\$
    BEGIN
      NEW.overview_embedding := google_ml.textembedding-gecko@003', NEW.overview)::vector;
      RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE TRIGGER overview_update_trigger
    BEFORE INSERT OR UPDATE OF overview ON investments
    FOR EACH ROW
    EXECUTE PROCEDURE update_overview_embedding();
    
    -- Analysis overview and function
    CREATE OR REPLACE FUNCTION update_analysis_embedding() RETURNS trigger AS \$\$
    BEGIN
      NEW.analysis_embedding := google_ml.embedding('textembedding-gecko@003', NEW.analysis)::vector;
      RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;
    
    CREATE OR REPLACE TRIGGER analysis_update_trigger
    BEFORE INSERT OR UPDATE OF analysis ON investments
    FOR EACH ROW
    EXECUTE PROCEDURE update_analysis_embedding();
    
    EOF
    )

    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos
    ```

1. Template:

    ```bash
    sql=$( cat <<EOF
    SELECT CURRENT_TIMESTAMP;
    EOF
    )

    echo $sql | PGPASSWORD=${OMNI_PW} psql -h "${OMNI_IP}" -U postgres -d ragdemos
    ```
