#!/bin/bash

curl -X PATCH http://localhost:8000/solutions \
  -H "csm-key: $CSM_KEY" \
  -H 'Content-Type: application/json'
