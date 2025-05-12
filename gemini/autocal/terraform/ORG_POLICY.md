# Org Policy Instructions

If you wish to configure Org Policy with terraform (and have set `org_policies` to `true`) then you will need a service account. The script `create-terraform-sa.sh` can create this for you:

```sh
export PROJECT_ID=xx
./create-terraform-sa.sh
```

Alternatively, create the SA yourself - you will need to have the Service Account Token Creator IAM role granted to your own user account. You can read more about this [on this Google Cloud blog post](https://cloud.google.com/blog/topics/developers-practitioners/using-google-cloud-service-account-impersonation-your-terraform-code)

When done, export the Service Account before using Terraform:

```sh
export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="terraform-builder@${PROJECT_ID}.iam.gserviceaccount.com"
```
