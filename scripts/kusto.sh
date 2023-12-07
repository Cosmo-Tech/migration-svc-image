#!/bin/bash


dblist=$(az kusto database list --cluster-name $SRC_CLUSTER_NAME -g $SRC_RESOURCE_GROUP -o json --query "[].name")
cat >kustos.json <<EOF
{
  "title": "migration kusto database",
  "steps": [
      "--kusto-iam",
      "--kusto-create",
      "--kusto-export",
      "--kusto-clone",
      "--kusto-ingest"
  ],
  "databases": $dblist
}
EOF
sed -i "s/$SRC_CLUSTER_NAME\///g" kustos.json
curl -X POST http://localhost:8000/kustos \
  -H "csm-key: $CSM_KEY" \
  -H 'Content-Type: application/json' -d @kustos.json
