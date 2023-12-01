#!/bin/bash

if [[ $REPLICAS == "" ]]; then
    echo "REPLICAS variable is missing"
    exit 1
fi

if [[ $K8S_NAMESPACE == "" ]]; then
    echo "K8S_NAMESPACE variable is missing"
    exit 1
fi

for i in $(seq 1 $REPLICAS);
do
    mypod=$(kubectl -n $K8S_NAMESPACE get pods | grep csm-deployment | awk "NR==$i{print \$1}")
    if [[ $mypod  != "" ]]; then
        echo $mypod
        port=$((8080+i))
        kubectl port-forward -n $K8S_NAMESPACE pod/$mypod  $port:8000 &
        echo -n "port-forward 8000 -> $port"
    else
        echo "pod not found"
    fi
done
