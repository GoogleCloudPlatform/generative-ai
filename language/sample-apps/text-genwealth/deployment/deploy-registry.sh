# Load env variables
source ./env.sh

# Update the Vertex AI configId
read -p "Enter the Vertex AI configId: " SEARCH_CONFIG_ID
echo "export SEARCH_CONFIG_ID=${SEARCH_CONFIG_ID}" >> env.sh

# Update org policies
echo "Updating org policies"
declare -a policies=("constraints/run.allowedIngress"
                "constraints/iam.allowedPolicyMemberDomains"
                )
for policy in "${policies[@]}"
do
cat <<EOF > new_policy.yaml
constraint: $policy
listPolicy:
 allValues: ALLOW
EOF
gcloud resource-manager org-policies set-policy new_policy.yaml --project=$PROJECT_ID
done

echo "Waiting 90 seconds for org policies to take effect"
sleep 90

#
# Create the Artifact Registry repository:
#
echo "Creating the Artifact Registry repository"
gcloud artifacts repositories create genwealth \
--repository-format=docker \
--location=$REGION \
--project=$PROJECT_ID 

# Make PDFs publically viewable
gcloud storage buckets add-iam-policy-binding gs://${PROJECT_ID}-docs \
    --member=allUsers --role=roles/storage.objectViewer
