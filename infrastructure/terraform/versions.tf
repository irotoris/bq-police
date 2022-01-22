terraform {
  required_version = ">= 0.13"
  required_providers {
    archive = {
      source = "hashicorp/archive"
    }
    google = {
      source  = "hashicorp/google"
      version = "4.7.0"
    }
  }
}
