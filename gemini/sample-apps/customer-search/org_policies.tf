#Enable services and organization policies

resource "google_org_policy_policy" "domain_restricted_sharing" {
  depends_on = [google_project_service.init]
  name       = "projects/${var.project}/policies/iam.allowedPolicyMemberDomains"
  parent     = "projects/${var.project}"

  spec {
    inherit_from_parent = false
    reset               = true
  }
}

resource "google_org_policy_policy" "shielded_vm" {
  depends_on = [google_project_service.init]
  name       = "projects/${var.project}/policies/compute.requireShieldedVm"
  parent     = "projects/${var.project}"

  spec {
    inherit_from_parent = false
    reset               = true
  }
}

resource "google_org_policy_policy" "external_ip_acess" {
  depends_on = [google_project_service.init]
  name       = "projects/${var.project}/policies/compute.vmExternalIpAccess"
  parent     = "projects/${var.project}"

  spec {
    inherit_from_parent = false
    rules {
      allow_all = "TRUE"
    }
  }
}

resource "google_project_service" "init" {
  provider = google-beta.no_user_project_override
  project  = var.project
  for_each = toset([
    "aiplatform.googleapis.com",
    "analyticshub.googleapis.com",
    "apphub.googleapis.com",
    "artifactregistry.googleapis.com",
    "automl.googleapis.com",
    "autoscaling.googleapis.com",
    "batch.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "bigquerymigration.googleapis.com",
    "bigqueryreservation.googleapis.com",
    "bigquerystorage.googleapis.com",
    "bigtable.googleapis.com",
    "bigtableadmin.googleapis.com",
    "chat.googleapis.com",
    "cloudaicompanion.googleapis.com",
    "cloudapis.googleapis.com",
    "cloudasset.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "compute.googleapis.com",
    "connectgateway.googleapis.com",
    "container.googleapis.com",
    "containerfilesystem.googleapis.com",
    "containerregistry.googleapis.com",
    "datacatalog.googleapis.com",
    # "dataflow.googleapis.com",
    "dataform.googleapis.com",
    # "dataplex.googleapis.com",
    "datastore.googleapis.com",
    "deploymentmanager.googleapis.com",
    "dialogflow.googleapis.com",
    "discoveryengine.googleapis.com",
    "distance-matrix-backend.googleapis.com",
    "dns.googleapis.com",
    "documentai.googleapis.com",
    "edgecache.googleapis.com",
    "eventarc.googleapis.com",
    "file.googleapis.com",
    "firebaserules.googleapis.com",
    "firestore.googleapis.com",
    "gkebackup.googleapis.com",
    "gkeconnect.googleapis.com",
    "gkehub.googleapis.com",
    "gmail.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "language.googleapis.com",
    "logging.googleapis.com",
    "looker.googleapis.com",
    "mesh.googleapis.com",
    "meshca.googleapis.com",
    "meshconfig.googleapis.com",
    "monitoring.googleapis.com",
    "multiclustermetering.googleapis.com",
    "networkconnectivity.googleapis.com",
    "networksecurity.googleapis.com",
    "networkservices.googleapis.com",
    "notebooks.googleapis.com",
    "opsconfigmonitoring.googleapis.com",
    "orgpolicy.googleapis.com",
    "oslogin.googleapis.com",
    "places-backend.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicedirectory.googleapis.com",
    "servicemanagement.googleapis.com",
    "serviceusage.googleapis.com",
    #"source.googleapis.com",
    "sourcerepo.googleapis.com",
    "sql-component.googleapis.com",
    "stackdriver.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
    "storage.googleapis.com",
    "timeseriesinsights.googleapis.com",
    "trafficdirector.googleapis.com",
    "translate.googleapis.com",
    "vision.googleapis.com",
    "visionai.googleapis.com",
    "workstations.googleapis.com",
    "dataform.googleapis.com",
    "orgpolicy.googleapis.com",
    "cloudbilling.googleapis.com",
    "identitytoolkit.googleapis.com",
    "firebase.googleapis.com",
  ])
  service = each.key

  # Don't disable the service if the resource block is removed by accident.
  disable_on_destroy = false
}

