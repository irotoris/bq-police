#####################
# log sink to pubsub
#####################
resource "google_logging_project_sink" "log_sink" {
  name        = var.module_name
  destination = "pubsub.googleapis.com/${google_pubsub_topic.log_sink.id}"
  filter      = <<-EOF
　resource.type="bigquery_resource"
  protoPayload.methodName="jobservice.jobcompleted"
  protoPayload.serviceData.jobCompletedEvent.eventName="query_job_completed"
  EOF

  unique_writer_identity = true
}

resource "google_pubsub_topic" "log_sink" {
  name = var.module_name
}

resource "google_pubsub_topic_iam_member" "log_sink" {
  project = google_pubsub_topic.log_sink.project
  topic   = google_pubsub_topic.log_sink.name
  role    = "roles/editor"
  member  = google_logging_project_sink.log_sink.writer_identity
}


##################
# functions
##################
resource "google_storage_bucket" "deploy_bucket" {
  name        = "${var.project_id}-${var.module_name}-deploy"
  location    = "us"
}

data "archive_file" "local_function_source" {
  type        = "zip"
  source_dir  = "../../src"
  output_path = "functions.zip"
}

resource "google_storage_bucket_object" "deploy_archive" {
  name   = "functions.${data.archive_file.local_function_source.output_md5}.zip"
  bucket = google_storage_bucket.deploy_bucket.name
  source = data.archive_file.local_function_source.output_path
}

resource "google_cloudfunctions_function" "function" {
  name        = var.module_name
  region      = "us-central1"
  description = "real-time query performance and billing alert"
  runtime     = "python39"

  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.deploy_bucket.name
  source_archive_object = google_storage_bucket_object.deploy_archive.name
  entry_point           = "run"
  timeout               = 60

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.log_sink.id
    failure_policy {
      retry = false
    }
  }

  environment_variables = {
    SLACK_WEBHOOK_URL = var.slack_webhook_url
  }

  depends_on = [
    google_storage_bucket_object.deploy_archive
  ]
}
