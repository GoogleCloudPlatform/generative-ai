<!-- BEGIN_TF_DOCS -->
Copyright 2024 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Purpose

Creates Datastore and Search engine by terraform.

Import data into the datastore created by terraform and run a search query.

## Implementation

Update terraform.tfvars and run 

```
terraform init
terraform plan
terraform apply
```

Once the terraform code runs succesfully it generates tfvars.json file in the directory specificed in outputs_location variable.

Once you have created the tfvars.json file, you can run the python code.

python main.py import - imports the specified documents from the given gcs_uri to the specified data store
python main.py search - it searches the data store for the specified search_query and prints the response.



## Resources

| Name | Type |
|------|------|
| [google_discovery_engine_data_store.datastore-ds](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/discovery_engine_data_store) | resource |
| [google_discovery_engine_search_engine.datastore-engine](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/discovery_engine_search_engine) | resource |
| [local_file.tfvars](https://registry.terraform.io/providers/hashicorp/local/latest/docs/resources/file) | resource |
| [random_id.id](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_company_name"></a> [company\_name](#input\_company\_name) | Name of company for which datastore is being created | `string` | n/a | yes |
| <a name="input_datastore_name"></a> [datastore\_name](#input\_datastore\_name) | Name of the datasore | `string` | n/a | yes |
| <a name="input_gcs_bucket_name"></a> [gcs\_bucket\_name](#input\_gcs\_bucket\_name) | GCS Bucket where input data will be loaded | `string` | n/a | yes |
| <a name="input_gcs_region"></a> [gcs\_region](#input\_gcs\_region) | GCS Bucket region where input data will be loaded | `string` | n/a | yes |
| <a name="input_outputs_location"></a> [outputs\_location](#input\_outputs\_location) | Locaton of tfvars file where outputs will be stored | `string` | `null` | no |
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | DevOps Project ID | `string` | n/a | yes |
| <a name="input_region"></a> [region](#input\_region) | Region where the resources will be created | `string` | `"us-central1"` | no |

## Outputs

No outputs.
<!-- END_TF_DOCS -->