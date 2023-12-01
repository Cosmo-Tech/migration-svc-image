# Cosmo-Tech - migration azure resources

## Prerequisites

* `helm`
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


## Setup variables

```bash
export K8S_NAMESPACE=<NAMESPACE>
export K8S_CONTEXT=
export REPLICAS=
export MIGRATION_IMAGE_VERSION=<MIGRATION_IMAGE_VERSION>

export SRC_CLUSTER=<SOURCE_CLUSTER_URI>
export SRC_CLUSTER_NAME=
export SRC_RESOURCE_GROUP=
export SRC_ACCOUNT_KEY=

export DEST_CLUSTER=<DEST_CLUSTER_URI>
export DEST_RESOURCE_GROUP=
export DEST_ACCOUNT_KEY=

export MIGRATION_CLIENT_ID=
export MIGRATION_CLIENT_SECRET=
export AZURE_SUBSCRIPTION_ID=
export AZURE_TENANT_ID=

export ACCOUNT_EXPORT_NAME=
export ACCOUNT_EXPORT_SECRET=

export REDIS_HOST=<REDIS_SERVICE_NAME>.<NAMESPACE>.svc.cluster.local
export REDIS_PORT=6379
export REDIS_USERNAME=default
export REDIS_PASSWORD=
export CSM_KEY=
```

## Fill values.yaml

* Create a values.yaml with environment variables

```yaml
cat >values.yaml <<EOF
image:
  repository: ghcr.io/cosmo-tech/migration-svc-image
  tag: $MIGRATION_IMAGE_VERSION
replicas: $REPLICAS
nodeSize: "highcpu"
resources:
  limits:
    cpu: "30"
    memory: 50Gb
  requests:
    cpu: "15"
    memory: 25Gb
env:
  SRC_CLUSTER: $SRC_CLUSTER
  SRC_RESOURCE_GROUP: $SRC_RESOURCE_GROUP
  SRC_ACCOUNT_KEY: $SRC_ACCOUNT_KEY
  DEST_CLUSTER: $DEST_CLUSTER 
  DEST_RESOURCE_GROUP: $DEST_RESOURCE_GROUP 
  DEST_ACCOUNT_KEY: $DEST_ACCOUNT_KEY
  MIGRATION_CLIENT_ID: $MIGRATION_CLIENT_ID 
  MIGRATION_CLIENT_SECRET: $MIGRATION_CLIENT_SECRET 
  AZURE_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID
  AZURE_TENANT_ID: $AZURE_TENANT_ID
  ACCOUNT_EXPORT_NAME: $ACCOUNT_EXPORT_NAME 
  ACCOUNT_EXPORT_SECRET: $ACCOUNT_EXPORT_SECRET 
  REDIS_HOST: $REDIS_HOST
  REDIS_PORT: $REDIS_PORT
  REDIS_USERNAME: $REDIS_USERNAME  
  REDIS_PASSWORD: $REDIS_PASSWORD 
  CSM_KEY: $CSM_KEY
EOF
```

## Pull helm chart 

```bash
helm pull oci://ghcr.io/cosmo-tech/migration-svc-charts --version $MIGRATION_IMAGE_VERSION
```

## Install helm chart in destination AKS cluster

```bash
kubectl config use-context $K8S_CONTEXT
```
```bash
helm -n $K8S_NAMESPACE install \
  -f values.yaml csm-migration-svc migration-svc-charts-$MIGRATION_IMAGE_VERSION.tgz
```

## Port forwarding

```bash
./forwarding.sh
```

## Storages

```bash
curl -X POST http://localhost:PORT/storages -H "csm-key: ${CSM_KEY}"
```

## Solutions

```bash
curl -X PATCH http://localhost:PORT/solutions -H "csm-key: ${CSM_KEY}"
```

## Kusto

* List kusto databases from adx cluster source

```bash
az kusto database list --cluster-name $SRC_CLUSTER_NAME \
  --resource-group $SRC_RESOURCE_GROUP -o json --query "[].name" > kustos.databases.json
```
```bash
# remove <MyClusterName> string
sed -i "s/$SRC_CLUSTER_NAME\///g" kustos.databases.json
```

```bash
curl -X POST http://localhost:PORT/kustos \
  -H "csm-key: ${CSM_KEY}" \
  -H 'Content-Type: application/json' -d '{
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

## Clean up

* Remove Owner role in source and destination resource group
* Delete the app registration
* Delete the storage account

* Uninstall service
```bash
helm -n $K8S_NAMESPACE uninstall csm-migration-svc
```