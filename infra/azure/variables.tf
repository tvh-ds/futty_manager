variable "subscription_id" {
  type = string
}
variable "project" {
  type    = string
  default = "scout"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,15}$", var.project))
    error_message = "Project must be a short lowercase Azure name."
  }
}
variable "location" {
  type    = string
  default = "westeurope"
}
variable "deploy_api" {
  type    = bool
  default = false
}
variable "api_image" {
  type    = string
  default = "ghcr.io/owner/scout-api:replace-with-release"
}
variable "allow_synthetic" {
  type    = bool
  default = false
}
variable "monthly_budget" {
  type    = number
  default = 10
}
variable "budget_start" {
  type        = string
  description = "First of this month in UTC, e.g. 2026-10-01T00:00:00Z."
}
variable "budget_email" {
  type = string
}
variable "github_repository" {
  type        = string
  description = "GitHub owner/repository for federated deployment authentication."
}
