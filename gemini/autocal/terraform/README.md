# Terraform Setup

**Note:** You must [run this as a service account](https://cloud.google.com/blog/topics/developers-practitioners/using-google-cloud-service-account-impersonation-your-terraform-code) due to Organisation Policies being used. You can run [create-terraform-sa.sh](./create-terraform-sa.sh) to create one called `terraform-builder@${PROJECT_ID}.iam.gserviceaccount.com`.

This sets up 80-90% of the required infrastructure for the app. You will still need to do some manual work.

## Configuration

Copy `terraform.tfvars.example` to `terraform.tfvars`.

**Note**: If you plan on configuring org policy, you must run this as a service account. See [ORG_POLICY.md](ORG_POLICY.md) for instructions on doing this.

If you do not need to change org policy with terraform (or you will change it manually) you can run this as a regular user.

Now run the usual terraform steps:

```sh
terraform init
terraform plan
terraform apply
```

## Troubleshooting

Note: The Eventarc agent can sometimes fail the first time. If this happens, re-apply terraform configuration after a short wait:

```sh
terraform apply
```
