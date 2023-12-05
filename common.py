import os
import sys

from pydantic import BaseModel


def pars_env():
    args = dict()
    for i in [
        'SRC_CLUSTER',
        'SRC_RESOURCE_GROUP',
        "SRC_ACCOUNT_KEY",
        'DEST_CLUSTER',
        'DEST_RESOURCE_GROUP',
        "DEST_ACCOUNT_KEY",
        'MIGRATION_CLIENT_ID',
        'MIGRATION_CLIENT_SECRET',
        'AZURE_SUBSCRIPTION_ID',
        'AZURE_TENANT_ID',
        'ACCOUNT_EXPORT_NAME',
        'ACCOUNT_EXPORT_SECRET',
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_USERNAME",
        "REDIS_PASSWORD",
        "CSM_KEY"
    ]:
        if i not in os.environ:
            print(f"{i} is missing")
            sys.exit(1)
        args.setdefault(i, os.environ.get(i))
    return args


class BodyStorage(BaseModel):
    title: str
    storage_src: str
    storage_dest: str


class BodyKusto(BaseModel):
    title: str
    steps: list
    databases: list


class BodyKustoTest(BaseModel):
    title: str
    databases: list
