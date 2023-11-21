# Cosmo-Tech - migration azure resources - platform 2.4 to 3.0

## Prerequisites

* helm >= v3.13.2
* docker
* k9s


* Create an app registration in azure portal

    * Sign in to the Azure portal
    * Navigate to the Azure portal and select the Azure AD service
    * Select the App Registrations blade on the left, then select New registration
    * In the Register an application page that appears, enter your application's registration information:
        * In the Name section, enter a meaningful application name that will be displayed to users of the app.
        * Under Supported account types, select Accounts in this organizational directory only.
        * Select Register to create the application.
        * In the app's registration screen, find and note the Application (client) ID. You use this value later.
        * Create a client secret and note it. You use this value later.

> **Important**    

* Make sure to remove all permissions for all "`AAD object id failed to be resolved`" item in each database azure data explorer (if exists)
* Make sure to assign with `system-assigned` all connections with event hubs in each database azure data explorer  
* Assign the Owner role in resource group for source and destination platform


## Create a storage account
* You will need the name and secret key value later)

## Pull helm chart 

```bash
helm pull oci://ghcr.io/cosmo-tech/migration-svc-chart --version 1.0.0
```

## Setup values.yaml

* Create a values.yaml with environment variables

```yaml
image:
  repository: ghcr.io/cosmo-tech/migration-svc-image
  tag: latest
env:
  SRC_CLUSTER: <SRC_CLUSTER_URI> e.g. https://<CLUSTER_NAME>.<LOCATION>.kusto.windows.com
  SRC_RESOURCE_GROUP: <SRC_RESOURCE_GROUP_NAME>
  SRC_ACCOUNT_KEY: <SRC_ACCOUNT_KEY> 
  DEST_CLUSTER: <DEST_CLUSTER_URI> e.g. https://<CLUSTER_NAME>.<LOCATION>.kusto.windows.com 
  DEST_RESOURCE_GROUP: <DEST_RESOURCE_GROUP_NAME> 
  DEST_ACCOUNT_KEY: <DEST_ACCOUNT_KEY> 
  MIGRATION_CLIENT_ID: <MIGRATION_CLIENT_ID> 
  MIGRATION_CLIENT_SECRET: <MIGRATION_CLIENT_SECRET> 
  AZURE_SUBSCRIPTION_ID: <AZURE_SUBSCRIPTION_ID> 
  AZURE_TENANT_ID: <AZURE_TENANT_ID> 
  ACCOUNT_EXPORT_NAME: <ACCOUNT_EXPORT_NAME> 
  ACCOUNT_EXPORT_SECRET: <ACCOUNT_EXPORT_SECRET> 
  REDIS_HOST: <REDIS_HOST> e.g. <REDIS_SERVICE_NAME>.<NAMESPACE>.svc.cluster.local 
  REDIS_PORT: <REDIS_PORT>
  REDIS_USERNAME: <REDIS_USERNAME> 
  REDIS_PASSWORD: <REDIS_PASSWORD> 
  CSM_KEY: <CSM_KEY>
  ```

## Install helm chart

```bash
kubectl config use-context <CONTEXT>
helm -n <namespace> install -f values.yaml csm-migration-svc migration-svc-chart-1.0.0.tgz
```

## Clean up

* Remove Owner role in source and destination resource group
* Delete the app registration
* Delete the storage account

* Uninstall service
```bash
helm -n <namespace> uninstall csm-migration-svc
```