#!/bin/bash

cat >storages.json <<EOF
{
  "title": "migration csm storage test",
  "storage_src": "$SRC_STORAGE_NAME",
  "storage_dest": "$DEST_STORAGE_NAME"
}
EOF
curl -X POST http://localhost:8000/storages \
  -H "csm-key: ${CSM_KEY}" \
  -H 'Content-Type: application/json' -d @storages.json
