locals {
  suffix = substr(sha256("${var.subscription_id}/${var.project}"), 0, 8)
  tags   = { ScoutProject = var.project, ManagedBy = "Terraform" }
}

resource "azurerm_resource_group" "scout" {
  name     = "${var.project}-portfolio"
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "scout" {
  name                            = "scout${local.suffix}"
  resource_group_name             = azurerm_resource_group.scout.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

resource "azurerm_storage_container" "private" {
  for_each              = toset(["raw", "releases", "backups", "tfstate"])
  name                  = each.value
  storage_account_id    = azurerm_storage_account.scout.id
  container_access_type = "private"
}

resource "azurerm_user_assigned_identity" "api" {
  name                = "${var.project}-api"
  location            = var.location
  resource_group_name = azurerm_resource_group.scout.name
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "deploy" {
  name                = "${var.project}-deploy"
  location            = var.location
  resource_group_name = azurerm_resource_group.scout.name
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "github" {
  name                = "github-production"
  resource_group_name = azurerm_resource_group.scout.name
  parent_id           = azurerm_user_assigned_identity.deploy.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${var.github_repository}:environment:production"
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "scout" {
  name                       = "scout-${local.suffix}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.scout.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = true
  tags                       = local.tags
}

resource "azurerm_role_assignment" "api_secrets" {
  scope                = azurerm_key_vault.scout.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

resource "azurerm_role_assignment" "api_releases" {
  scope                = azurerm_storage_container.private["releases"].id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

resource "azurerm_role_assignment" "deploy_resources" {
  scope                = azurerm_resource_group.scout.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.deploy.principal_id
}

resource "azurerm_role_assignment" "deploy_storage" {
  scope                = azurerm_storage_account.scout.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.deploy.principal_id
}

resource "azurerm_role_assignment" "deploy_secrets" {
  scope                = azurerm_key_vault.scout.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.deploy.principal_id
}

resource "azurerm_log_analytics_workspace" "scout" {
  name                = "${var.project}-logs"
  location            = var.location
  resource_group_name = azurerm_resource_group.scout.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 0.05
  tags                = local.tags
}

resource "azurerm_application_insights" "scout" {
  name                 = "${var.project}-traces"
  location             = var.location
  resource_group_name  = azurerm_resource_group.scout.name
  workspace_id         = azurerm_log_analytics_workspace.scout.id
  application_type     = "web"
  sampling_percentage  = 10
  daily_data_cap_in_gb = 0.05
  tags                 = local.tags
}

resource "azurerm_static_web_app" "scout" {
  name                = "${var.project}-frontend"
  location            = var.location
  resource_group_name = azurerm_resource_group.scout.name
  sku_tier            = "Free"
  sku_size            = "Free"
  tags                = local.tags
}

resource "azurerm_container_app_environment" "scout" {
  name                       = "${var.project}-environment"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.scout.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.scout.id
  tags                       = local.tags
}

resource "azurerm_container_app" "scout" {
  count                        = var.deploy_api ? 1 : 0
  name                         = "${var.project}-api"
  resource_group_name          = azurerm_resource_group.scout.name
  container_app_environment_id = azurerm_container_app_environment.scout.id
  revision_mode                = "Single"
  tags                         = local.tags
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }
  secret {
    name                = "database-url"
    identity            = azurerm_user_assigned_identity.api.id
    key_vault_secret_id = "${azurerm_key_vault.scout.vault_uri}secrets/scout-database-url"
  }
  template {
    min_replicas = 0
    max_replicas = 1
    container {
      name   = "api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1Gi"
      env {
        name        = "SCOUT_DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "SCOUT_ALLOW_SYNTHETIC"
        value = tostring(var.allow_synthetic)
      }
      env {
        name  = "SCOUT_CORS_ORIGINS"
        value = jsonencode(["https://${azurerm_static_web_app.scout.default_host_name}"])
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.scout.connection_string
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.api.client_id
      }
      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health/live"
      }
      readiness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health/ready"
      }
    }
    http_scale_rule {
      name                = "requests"
      concurrent_requests = "20"
    }
  }
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
  depends_on = [azurerm_role_assignment.api_secrets]
}

resource "azurerm_consumption_budget_resource_group" "scout" {
  name              = "${var.project}-credit-alert"
  resource_group_id = azurerm_resource_group.scout.id
  amount            = var.monthly_budget
  time_grain        = "Monthly"
  time_period { start_date = var.budget_start }
  notification {
    enabled        = true
    threshold      = 70
    operator       = "GreaterThan"
    contact_emails = [var.budget_email]
  }
}
