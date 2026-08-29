terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "cocoon-prod-terraform-state"
    prefix = "terraform/state/production"
  }
}

provider "google" {
  project = "decent-genius-503000-h2"
  region  = "asia-southeast1"
}
