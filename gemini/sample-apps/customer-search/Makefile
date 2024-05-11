project_id={YOUR-PROJECT-ID}
repo_name={YOUR-ARTIFACT-REGISTRY-REPO-NAME}
region=us-central1

deploy_resources:
	gcloud storage cp -r  gs://github-repo/generative-ai/sample-apps/customer-search files/
	mv -v files/customer-search/* files/
	rm -r files/customer-search
	mkdir -p CymbalBankWebDeployed/assets
	mv files/assets/ CymbalBankWebDeployed/assets
	rm -r files/assets
	rm -r files/images
	terraform init 
	terraform apply -auto-approve
	terraform output > output_urls.txt
	python3 dialogflow.py

deploy_website:
	gcloud config set project $(project_id)
	gcloud auth configure-docker
	gcloud services enable artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com
	cd CymbalBankWebDeployed && gcloud builds submit --tag $(region)-docker.pkg.dev/$(project_id)/$(repo_name)/cymbal_bank:1.0.0 && gcloud run deploy cymbal_bank --image $(region)-docker.pkg.dev/$(project_id)/$(repo_name)/cymbal_bank:1.0.0 --region $(region) --allow-unauthenticated