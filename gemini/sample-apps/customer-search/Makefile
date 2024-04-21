project_id=terraform-test-project-406510#{YOUR-PROJECT-ID}
repo_name=terraform-test-project-406510-website-repo#{YOUR-ARTIFACT-REGISTRY-REPO-NAME}
region=us-central1

deploy_resources:
	terraform init 
	terraform apply -auto-approve
	terraform output > output_urls.txt
	gcloud storage cp gs://public_bucket_fintech_app/CymBuddy_DF_template/CymBuddy.json files/
	python3 dialogflow.py

deploy_website:
	gcloud config set project $(project_id)
	gcloud auth configure-docker
	gcloud services enable artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com
	cd files/CymbalBankWebDeployed && gcloud builds submit --tag $(region)-docker.pkg.dev/$(project_id)/$(repo_name)/cymbal_bank:1.0.0 && gcloud run deploy cymbal_bank --image $(region)-docker.pkg.dev/$(project_id)/$(repo_name)/cymbal_bank:1.0.0 --region $(region) --allow-unauthenticated