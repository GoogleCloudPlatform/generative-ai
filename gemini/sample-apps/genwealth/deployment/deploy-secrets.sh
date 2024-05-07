#!/usr/bin/env bash

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

# Prompt user to create the AlloyDB password
read -r -s -p "Enter a password for the AlloyDB cluster: " ALLOYDB_PASSWORD
echo ""

# Prompt user to create the pgAdmin password
read -r -s -p "Enter a password for pgAdmin: " PGADMIN_PASSWORD
echo ""

# Create AlloyDB password secret
gcloud secrets create alloydb-password-"${PROJECT_ID}" \
  --replication-policy="automatic"

echo -n "$ALLOYDB_PASSWORD" |
  gcloud secrets versions add alloydb-password-"${PROJECT_ID}" --data-file=-

# Create pgAdmin password secret
gcloud secrets create pgadmin-password-"${PROJECT_ID}" \
  --replication-policy="automatic"

echo -n "$PGADMIN_PASSWORD" |
  gcloud secrets versions add pgadmin-password-"${PROJECT_ID}" --data-file=-

sleep 5
