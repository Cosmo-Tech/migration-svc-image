# Cosmo-Tech - migration azure resources

## Prerequisites

* `helm`
* `postman`
* `docker`
* `k9s`
* `Destination AKS cluster running`
* `Destination ADX cluster running`
* `Create an app registration in azure portal`

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
* You will need the name and secret key value later

## Pull helm chart 

```bash
helm pull oci://ghcr.io/cosmo-tech/migration-svc-charts --version <version>
```

## Fill values.yaml

* Create a values.yaml with environment variables

```yaml
image:
  repository: ghcr.io/cosmo-tech/migration-svc-image
  tag: <version>
env:
  SRC_CLUSTER: <SRC_CLUSTER_URI> e.g. https://<CLUSTER_NAME>.<LOCATION>.kusto.windows.net
  SRC_RESOURCE_GROUP: <SRC_RESOURCE_GROUP_NAME>
  SRC_ACCOUNT_KEY: <SRC_ACCOUNT_KEY> 
  DEST_CLUSTER: <DEST_CLUSTER_URI> e.g. https://<CLUSTER_NAME>.<LOCATION>.kusto.windows.net 
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

## Install helm chart in destination AKS cluster

```bash
kubectl config use-context <CONTEXT>
helm -n <namespace> install -f values.yaml csm-migration-svc migration-svc-charts-<version>.tgz
```

> Example:
  * cluster name: phoenixAKSdev
  * namepace: phoenix
  * version: 1.0.5

  ```bash
  kubectl config use-context phoenixAKSdev
  helm -n phoenix install -f values.yaml csm-migration-svc migration-svc-charts-1.0.5.tgz
  ```


## Migration endpoints

### Kusto

* List kusto databases from adx cluster source

```bash
az kusto database list --cluster-name MyCluster --resource-group MyResourceGroup -o json --query "[].name" > kustos.databases.json
```
```bash
sed -i 's/<MyCluster>\///g' kustos.databases.json
```

> Example:
  * cluster name: phoenixdev
  * resource group: phoenixdev

  ```bash
  az kusto database list --cluster-name phoenixdev --resource-group phoenixdev -o json --query "[].name" > kustos.databases.json
  ```
  ```bash
  sed -i 's/phoenixdev\///g' kustos.databases.json
  ```

* Replace the list `kustos.databases.json` in `databases` key

```bash
curl -X POST http://localhost:8080/kustos -H 'csm-key: <CSM-KEY>' -H 'Content-Type: application/json' -d '
{
    "title": "migration kusto database",
    "steps": [
        "--kusto-iam",
        "--kusto-create",
        "--kusto-export",
        "--kusto-clone",
        "--kusto-ingest",
        "--overwrite"
    ],
    "databases": [
        "database1",
        "database2",
        ...
    ]
}'
```

### Storage

```bash
curl -X POST http://localhost:8080/storages -H 'csm-key: <CSM-KEY>' -H 'Content-Type: application/json' -d '
{
    "title": "migration storage",
    "storage_src": "<STORAGE_SOURCE>",
    "storage_dest": "<STORAGE_DESTINATION>"
}'
```

### Solutions

```bash
curl -X PATCH http://localhost:8080/solutions -H 'csm-key: <CSM-KEY>'
```

## Clean up

* Remove Owner role in source and destination resource group
* Delete the app registration
* Delete the storage account

* Uninstall service
```bash
helm -n <namespace> uninstall csm-migration-svc
```