###
### Deploys the genwealth database to AlloyDB
###

# Prompt user to create the AlloyDB password
read -s -p "Enter a password for the AlloyDB cluster: " ALLOYDB_PASSWORD
echo ""

# Prompt user to create the pgAdmin password
read -s -p "Enter a password for pgAdmin: " PGADMIN_PASSWORD
echo ""

# Enable Backend APIs
echo "Enabling APIs"
PROJECT_ID=$(gcloud config get-value project 2> /dev/null)
gcloud services enable iam.googleapis.com --project ${PROJECT_ID}
gcloud services enable compute.googleapis.com --project ${PROJECT_ID}
gcloud services enable storage-component.googleapis.com --project ${PROJECT_ID}
gcloud services enable pubsub.googleapis.com --project ${PROJECT_ID}
gcloud services enable cloudkms.googleapis.com --project ${PROJECT_ID}
gcloud services enable logging.googleapis.com --project ${PROJECT_ID}
gcloud services enable alloydb.googleapis.com --project ${PROJECT_ID}
gcloud services enable servicedirectory.googleapis.com --project ${PROJECT_ID}
gcloud services enable serviceusage.googleapis.com --project ${PROJECT_ID}
gcloud services enable networkmanagement.googleapis.com --project ${PROJECT_ID}
gcloud services enable cloudresourcemanager.googleapis.com --project ${PROJECT_ID}
gcloud services enable servicenetworking.googleapis.com --project ${PROJECT_ID}
gcloud services enable dns.googleapis.com --project ${PROJECT_ID}
gcloud services enable orgpolicy.googleapis.com --project ${PROJECT_ID}
gcloud services enable aiplatform.googleapis.com --project ${PROJECT_ID}

# Enable pipeline APIs
gcloud services enable cloudfunctions.googleapis.com --project ${PROJECT_ID}
gcloud services enable eventarc.googleapis.com --project ${PROJECT_ID}
gcloud services enable secretmanager.googleapis.com --project ${PROJECT_ID}
gcloud services enable vpcaccess.googleapis.com --project ${PROJECT_ID}
gcloud services enable documentai.googleapis.com --project ${PROJECT_ID}

# Enable front end APIs
gcloud services enable run.googleapis.com --project ${PROJECT_ID}
gcloud services enable artifactregistry.googleapis.com --project ${PROJECT_ID}
gcloud services enable cloudbuild.googleapis.com --project ${PROJECT_ID}

# Create AlloyDB password secret
gcloud secrets create alloydb-password-${PROJECT_ID} \
    --replication-policy="automatic"

echo -n "$ALLOYDB_PASSWORD" | \
    gcloud secrets versions add alloydb-password-${PROJECT_ID} --data-file=-

# Create pgAdmin password secret
gcloud secrets create pgadmin-password-${PROJECT_ID} \
    --replication-policy="automatic"

echo -n "$PGADMIN_PASSWORD" | \
    gcloud secrets versions add pgadmin-password-${PROJECT_ID} --data-file=-

sleep 5

# Load env variables
source ./env.sh

# Install necessary packages
sudo apt-get -y install jq

# Create VPC
echo "Creating VPC"
gcloud compute networks create ${VPC_NAME} --project=${PROJECT_ID} --subnet-mode=auto --mtu=1460 --bgp-routing-mode=regional

# Create an IP Allocation for Private Services Access
echo "Creating IP Allocation for PSA"
gcloud compute addresses create demo-psa-range \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --network=${VPC_NAME}

# Create the Private Services Access Connection
echo "Creating PSA connection"
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges="demo-psa-range" \
    --network=${VPC_NAME}

# Create AlloyDB Cluster
echo "Creating AlloyDB Cluster"
gcloud alloydb clusters create ${ALLOYDB_CLUSTER} \
    --database-version="POSTGRES_14" \
    --password=${ALLOYDB_PASSWORD} \
    --network=${VPC_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --allocated-ip-range-name="demo-psa-range"

# Create AlloyDB Primary Instance
echo "Creating AlloyDB Primary Instance"
gcloud alloydb instances create ${ALLOYDB_INSTANCE} \
    --instance-type=PRIMARY \
    --cpu-count=2 \
    --region=${REGION} \
    --cluster=${ALLOYDB_CLUSTER} \
    --project=${PROJECT_ID} \
    --ssl-mode="ALLOW_UNENCRYPTED_AND_ENCRYPTED"

# Create policy document to allow External IP for GCE Instance
echo "Creating necessary policy"
tee -a policy.json <<EOF
{
  "name": "projects/${PROJECT_NUMBER}/policies/compute.vmExternalIpAccess",
  "spec": {
    "rules": [
      {
        "values": {
          "allowedValues": [
            "projects/${PROJECT_ID}/zones/${ZONE}/instances/${GCE_INSTANCE}"
          ]
        }
      }
    ]
  }
}
EOF

# Set policy and cleanup file.
gcloud org-policies set-policy --project ${PROJECT_ID} ./policy.json
rm ./policy.json

# Wait for policy to apply
echo "Waiting 90 seconds for Org policy to apply..."
sleep 90

# Create GCE Instance for pgadmin
echo "Creating GCE instance for pgAdmin"
gcloud compute instances create ${GCE_INSTANCE} \
    --project=${PROJECT_ID} \
    --zone=${ZONE} \
    --machine-type=e2-standard-2 \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=${VPC_NAME} \
    --metadata=enable-oslogin=true \
    --provisioning-model=STANDARD \
    --service-account=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append,https://www.googleapis.com/auth/cloud-platform \
    --tags=${GCE_INSTANCE} \
    --create-disk=auto-delete=yes,boot=yes,device-name=${GCE_INSTANCE},image=projects/debian-cloud/global/images/debian-12-bookworm-v20240213,mode=rw,size=100,type=projects/${PROJECT_ID}/zones/${ZONE}/diskTypes/pd-ssd \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring 

# Add necessary permissions for GCE instance
echo "Adding permissions"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.admin" 

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.client"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/alloydb.databaseUser"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/discoveryengine.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/documentai.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/eventarc.eventReceiver"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/eventarc.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/ml.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/pubsub.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageConsumer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.admin"

# Create Firewall Rule
echo "Creating firewall rule for pgAdmin instance"
gcloud compute firewall-rules create pgadmin-firewall --project=${PROJECT_ID} --direction=INGRESS --priority=1000 --network=${VPC_NAME} --action=ALLOW --rules=tcp:80,tcp:22 --source-ranges="${LOCAL_IPV4}/32",35.235.240.0/20 --target-tags=${GCE_INSTANCE}

# Allow ssh from cloud shell
gcloud compute firewall-rules create --network=$VPC_NAME default-allow-ssh --allow=tcp:22
echo "Waiting for firewall rules to take effect"
sleep 30

# Run script against pgadmin instance
gcloud compute ssh $GCE_INSTANCE --zone=$ZONE --command="rm -f /tmp/install-pgadmin.sh"
gcloud compute ssh $GCE_INSTANCE --zone=$ZONE --command="rm -f /tmp/env.sh"
gcloud compute copy-files ./deployment/install-pgadmin.sh $GCE_INSTANCE:/tmp/install-pgadmin.sh --zone=$ZONE
gcloud compute copy-files ./env.sh $GCE_INSTANCE:/tmp/env.sh --zone=$ZONE
gcloud compute ssh $GCE_INSTANCE --zone=$ZONE --command="chmod +x /tmp/install-pgadmin.sh"
gcloud compute ssh $GCE_INSTANCE --zone=$ZONE --command="chmod +x /tmp/env.sh"
gcloud compute ssh $GCE_INSTANCE --zone=$ZONE --command="/tmp/install-pgadmin.sh"

#gcloud compute ssh $GCE_INSTANCE --zone=$ZONE
