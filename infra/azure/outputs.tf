output "resource_group" { value = azurerm_resource_group.scout.name }
output "storage_account" { value = azurerm_storage_account.scout.name }
output "key_vault" { value = azurerm_key_vault.scout.name }
output "frontend_url" { value = "https://${azurerm_static_web_app.scout.default_host_name}" }
output "api_url" { value = try("https://${azurerm_container_app.scout[0].latest_revision_fqdn}", null) }
output "github_client_id" { value = azurerm_user_assigned_identity.deploy.client_id }
output "tenant_id" { value = data.azurerm_client_config.current.tenant_id }
