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


## 1.0 Create a storage account
* You will need the name and secret key value later


## 2.0 Setup variables

```bash
export K8S_NAMESPACE=<NAMESPACE>
export K8S_CONTEXT=
export REPLICAS=
export MIGRATION_IMAGE_VERSION=<MIGRATION_IMAGE_VERSION>

export SRC_CLUSTER=<SOURCE_CLUSTER_URI>
export SRC_CLUSTER_NAME=
export SRC_RESOURCE_GROUP=
export SRC_ACCOUNT_KEY=
export SRC_STORAGE_NAME=

export DEST_CLUSTER=<DEST_CLUSTER_URI>
export DEST_RESOURCE_GROUP=
export DEST_ACCOUNT_KEY=
export DEST_STORAGE_NAME=

export REDIS_HOST=<REDIS_SERVICE_NAME>.<NAMESPACE>.svc.cluster.local
export REDIS_PORT=6379
export REDIS_USERNAME=default
export REDIS_PASSWORD=

# app registration
export MIGRATION_CLIENT_ID=
export MIGRATION_CLIENT_SECRET=
export AZURE_SUBSCRIPTION_ID=
export AZURE_TENANT_ID=

# account storage backend
export ACCOUNT_EXPORT_NAME=
export ACCOUNT_EXPORT_SECRET=
export CSM_KEY=
```

## 3.0 Fill values.yaml

* Create a values.yaml with environment variables

```yaml
cat >values.yaml <<EOF
image:
  repository: ghcr.io/cosmo-tech/migration-svc-image
  tag: $MIGRATION_IMAGE_VERSION
replicaCount: $REPLICAS
nodeSize: highmemory
resources:
  limits:
    cpu: "15"
    memory: "100Gi"
  requests:
    cpu: "10"
    memory: "100Gi"
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

## 4.0 Pull helm chart 
```bash
helm pull oci://ghcr.io/cosmo-tech/migration-svc-charts --version $MIGRATION_IMAGE_VERSION
```

## 5.0 Install helm chart
```bash
kubectl config use-context $K8S_CONTEXT
```
```bash
helm -n $K8S_NAMESPACE install -f values.yaml csm-migration-svc migration-svc-charts-$MIGRATION_IMAGE_VERSION.tgz
```

## 6.0 Port forwarding service
```bash
kubectl port-forward svc/csm-service 8000:31001 -n $K8S_NAMESPACE &
```

## 7.0 Run scripts

### 7.1 blob migration
```bash
wget https://github.com/Cosmo-Tech/migration-svc-image/blob/main/scripts/storage.sh
```
```bash
chmod +x storage.sh
./storage.sh
```

### 7.2 Cosmo-Tech Solutions
```bash
wget https://github.com/Cosmo-Tech/migration-svc-image/blob/main/scripts/solution.sh
```
```bash
chmod +x solution.sh
./solution.sh
```

### 7.3 Kusto migration
```bash
wget https://github.com/Cosmo-Tech/migration-svc-image/blob/main/scripts/kusto.sh
```
```bash
chmod +x kusto.sh
./kusto.sh
```

## 8.0 Troubleshooting

### 8.1 Re-install service
```bash
helm -n $K8S_NAMESPACE uninstall csm-migration-svc
helm -n $K8S_NAMESPACE install -f values.yaml csm-migration-svc migration-svc-charts-$MIGRATION_IMAGE_VERSION.tgz
kubectl port-forward svc/csm-service 8000:31001 -n $K8S_NAMESPACE &
```

### 8.2 Run the script that ended up with problems

## 9.0 Clean-up

* Remove Owner role in source and destination resource group
* Delete the app registration
* Delete the storage account

* Uninstall service
```bash
helm -n $K8S_NAMESPACE uninstall csm-migration-svc
```