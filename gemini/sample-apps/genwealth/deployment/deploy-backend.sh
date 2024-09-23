#!/usr/bin/env bash

###
### Deploys the genwealth database to AlloyDB
###

# Load env variables
source ./env.sh

# Install necessary packages
sudo apt-get -y install jq

# Create VPC
echo "Creating VPC"
gcloud compute networks create "${VPC_NAME}" --project="${PROJECT_ID}" --subnet-mode=auto --mtu=1460 --bgp-routing-mode=regional

# Create an IP Allocation for Private Services Access
echo "Creating IP Allocation for PSA"
gcloud compute addresses create demo-psa-range \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network="${VPC_NAME}"

# Create the Private Services Access Connection
echo "Creating PSA connection"
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges="demo-psa-range" \
  --network="${VPC_NAME}"

# Create AlloyDB Cluster
echo "Creating AlloyDB Cluster"
gcloud alloydb clusters create "${ALLOYDB_CLUSTER}" \
  --database-version="POSTGRES_14" \
  --password="${ALLOYDB_PASSWORD}" \
  --network="${VPC_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --allocated-ip-range-name="demo-psa-range"

# Create AlloyDB Primary Instance
echo "Creating AlloyDB Primary Instance"
gcloud alloydb instances create "${ALLOYDB_INSTANCE}" \
  --instance-type=PRIMARY \
  --cpu-count=2 \
  --availability-type=ZONAL \
  --region="${REGION}" \
  --cluster="${ALLOYDB_CLUSTER}" \
  --project="${PROJECT_ID}" \
  --ssl-mode="ALLOW_UNENCRYPTED_AND_ENCRYPTED" \
  --database-flags=google_ml_integration.enable_model_support=on

# Create GCE Instance for pgadmin
echo "Creating GCE instance for pgAdmin"
gcloud compute instances create "${GCE_INSTANCE}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type=e2-standard-2 \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet="${VPC_NAME}" \
  --metadata=enable-oslogin=true \
  --provisioning-model=STANDARD \
  --service-account="${PROJECT_NUMBER}"-compute@developer.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/cloud-platform \
  --tags="${GCE_INSTANCE}" \
  --create-disk=auto-delete=yes,boot=yes,device-name="${GCE_INSTANCE}",image=projects/debian-cloud/global/images/debian-12-bookworm-v20240213,mode=rw,size=100,type=projects/"${PROJECT_ID}"/zones/${ZONE}/diskTypes/pd-ssd \
  --shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring

# Add necessary permissions for GCE instance
echo "Adding permissions"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.client"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.databaseUser"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/discoveryengine.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/documentai.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/eventarc.eventReceiver"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/eventarc.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/ml.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/pubsub.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageConsumer"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

# Create Firewall Rule
echo "Creating firewall rule for pgAdmin instance"
gcloud compute firewall-rules create pgadmin-firewall --project="${PROJECT_ID}" --direction=INGRESS --priority=1000 --network="${VPC_NAME}" --action=ALLOW --rules=tcp:80,tcp:22 --source-ranges="${LOCAL_IPV4}/32",35.235.240.0/20 --target-tags="${GCE_INSTANCE}"

# Allow ssh from cloud shell
gcloud compute firewall-rules create --network="$VPC_NAME" "default-allow-ssh-${PROJECT_ID}" --allow=tcp:22
echo "Waiting for firewall rules to take effect"
sleep 30

# Run script against pgadmin instance
gcloud compute ssh "$GCE_INSTANCE" --zone="$ZONE" --command="rm -f /tmp/install-pgadmin.sh"
gcloud compute ssh "$GCE_INSTANCE" --zone="$ZONE" --command="rm -f /tmp/env.sh"
gcloud compute copy-files ./deployment/install-pgadmin.sh "$GCE_INSTANCE":/tmp/install-pgadmin.sh --zone="$ZONE"
gcloud compute copy-files ./env.sh "$GCE_INSTANCE":/tmp/env.sh --zone="$ZONE"
gcloud compute ssh "$GCE_INSTANCE" --zone="$ZONE" --command="chmod +x /tmp/install-pgadmin.sh"
gcloud compute ssh "$GCE_INSTANCE" --zone="$ZONE" --command="chmod +x /tmp/env.sh"
gcloud compute ssh "$GCE_INSTANCE" --zone="$ZONE" --command="/tmp/install-pgadmin.sh"
