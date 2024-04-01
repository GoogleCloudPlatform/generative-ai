# VPC Network database is on
export VPC_NETWORK=
export VPC_SUBNET=$VPC_NETWORK
## AlloyDB 
export ALLOYDB_IP=
export PGADMIN_USER=
export ALLOYDB_PASSWORD=
export PGADMIN_PASSWORD=
export PGPORT=5432
export PGDATABASE=ragdemos
export PGUSER=postgres
export PGHOST=${ALLOYDB_IP}
export PGPASSWORD=${ALLOYDB_PASSWORD}
export PROJECT_ID=$(gcloud config get-value project)
# GCS Bucket for storing prospectus PDFs
export PROSPECTUS_BUCKET= 
# Datastore ID used by Vertex S&C
export DATASTORE_ID= 
