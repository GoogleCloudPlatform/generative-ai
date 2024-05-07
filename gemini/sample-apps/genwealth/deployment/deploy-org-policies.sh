#!/usr/bin/env bash

# Load env variables
source ./env.sh

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
gcloud org-policies set-policy --project "${PROJECT_ID}" ./policy.json
rm ./policy.json

# Update org policies
echo "Updating org policies"
declare -a policies=("constraints/run.allowedIngress"
  "constraints/iam.allowedPolicyMemberDomains"
)
for policy in "${policies[@]}"; do
  cat <<EOF >new_policy.yaml
constraint: $policy
listPolicy:
  allValues: ALLOW
EOF
  gcloud resource-manager org-policies set-policy new_policy.yaml --project="$PROJECT_ID"
done

# Wait for policies to apply
echo "Waiting 90 seconds for Org policies to apply..."
sleep 90
