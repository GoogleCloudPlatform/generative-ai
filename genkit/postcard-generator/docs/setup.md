# Initial Setup

To deploy this app successfully you will need to run some initial configuration.

## Option 1: Automated Configuration (Recommended)

This repository includes the required terraform to configure and setup your project to run this demo.

### Terraform Config

Copy `terraform.tfvars.example` to `terraform.tfvars` and populate it for your environment.

Only set `firebase_app_hosting` to `true` if you have already setup a Firebase App Hosting backend manually, this cannot be done by terraform as of 2024-09-27. If in doubt, leave it set to `false`.

### Deploy with Terraform

Run the following commands

```sh
terraform init
terraform apply
```

You may need to use [Service Account Impersonation](https://cloud.google.com/blog/topics/developers-practitioners/using-google-cloud-service-account-impersonation-your-terraform-code) to successfully deploy.

### Configure App Environment

You need a `.env` file. You can either copy `.env.example` to `.env` and populate it manually or run this command from your terraform directory:

```sh
export PROJECT_ID="my-project-id"
echo "NEXT_PUBLIC_GOOGLE_MAPS_PUBLIC_API_KEY=$(terraform output -raw maps_public_api_key)\nGOOGLE_MAPS_API_SERVER_KEY=$(terraform output -raw maps_server_api_key)\nGOOGLE_CLOUD_PROJECT=${PROJECT_ID}\nAUTH_ENABLED=false" | tee ../.env
```

Verify your [.env](../.env) file is correct with appropriate `PROJECT_ID` and `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` values. Ensure `AUTH_ENABLED` is set to `false` unless you have followed the instructions to enable authentication in [the deployment guide](deploy.md).

You're done! Check out the [next steps](#post-setup) guide for what's next.

## Option 2: Manual Configuration

1. Create two API keys:
   1. Server Key
      - Include the following restrictions:
        - Routes
        - Static Maps
      - Store it in secrets manager with the name `GOOGLE_MAPS_API_SERVER_KEY`
   2. Client Key
      - Include the following restrictions:
        - JavaScript
        - Places
      - Store it in secrets manager with the name `NEXT_PUBLIC_GOOGLE_MAPS_PUBLIC_API_KEY`
2. In [the Firebase Console](https://console.firebase.google.com) enable this project as a Firebase project
3. Copy `.env.example` to `.env` in the root directory and populate it with appropraite values

## Post Setup

You can now run through either the [Firebase App Hosting Deployment](deploy.md) or [Demo Guide](demo.md).
