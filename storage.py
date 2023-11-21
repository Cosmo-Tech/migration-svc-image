import sys
from azure.storage.blob import BlobServiceClient
from common import BodyStorage, pars_env


def pass_blob_client(
        account_name: str,
        account_secret: str
):
    prefix = f"DefaultEndpointsProtocol=https;AccountName={account_name}"
    suffix = "EndpointSuffix=core.windows.net"
    c_str = f"{prefix};AccountKey={account_secret};{suffix}"
    blob_client = BlobServiceClient.from_connection_string(c_str)
    return blob_client


# FUNCTIONS #
def copy_blob(
    client_src: BlobServiceClient,
    client_dest: BlobServiceClient,
    container: str,
    blob: str
):
    try:
        src_blob_client = client_src.get_blob_client(
            container=container,
            blob=blob
        )
        data = src_blob_client.download_blob()
    except Exception as exp:
        print(exp)
        sys.exit(0)
    try:
        dest_blob_client = client_dest.get_blob_client(
            container=container,
            blob=blob
        )
        if not dest_blob_client.exists():
            dest_blob_client.upload_blob(data.readall())
    except Exception as exp:
        print(exp)
        sys.exit(0)


def retrieve_containers(
    src_blob_client: BlobServiceClient
):
    try:
        containers = list(src_blob_client.list_containers())
        return containers
    except Exception as exp:
        print(exp)
        return []


def create_container_in_destination(
    client_dest: BlobServiceClient,
    container: str
):
    try:
        container_client = client_dest.get_container_client(
            container=container
        )
        if not container_client.exists():
            container_client.create_container()
    except Exception as exp:
        print(exp)
        sys.exit(0)


def run_storage(body: BodyStorage):
    args = pars_env()
    storage_src = body.storage_src
    storage_dest = body.storage_dest
    account_key_src = args.get("SRC_ACCOUNT_KEY")
    account_key_dest = args.get("DEST_ACCOUNT_KEY")
    client_src = pass_blob_client(
        account_name=storage_src,
        account_secret=account_key_src
    )
    client_dest = pass_blob_client(
        account_name=storage_dest,
        account_secret=account_key_dest
    )
    containers = retrieve_containers(src_blob_client=client_src)
    if not len(containers):
        print('container not found')
        sys.exit(0)
    for c in containers:
        print(c['name'])
        create_container_in_destination(
            client_dest=client_dest,
            container=c['name']
        )
        container_client = client_src.get_container_client(
            container=c['name']
        )
        blobs = container_client.list_blobs()
        for blo in blobs:
            copy_blob(
                client_src=client_src,
                client_dest=client_dest,
                container=c['name'],
                blob=blo['name']
            )
    print("Successfully Completed")
