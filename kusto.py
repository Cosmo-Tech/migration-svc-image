import re
import sys
import yaml
import time

from uuid import uuid4
from functools import wraps
from datetime import datetime
from datetime import timedelta
from typing import Any, Callable
from azure.identity import ClientSecretCredential
from azure.mgmt.kusto import KustoManagementClient
from azure.mgmt.kusto.models import ReadWriteDatabase, CheckNameRequest
from azure.mgmt.kusto.models import DatabasePrincipalAssignment
from azure.kusto.data import KustoClient
from azure.kusto.data import KustoConnectionStringBuilder as Kusto
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from common import BodyKusto, pars_env


# DECORATORS #
def generate_sas_token(blob_name: str, container: str):
    _args = pars_env()
    account_name = _args.get('ACCOUNT_EXPORT_NAME')
    account_secret = _args.get('ACCOUNT_EXPORT_SECRET')
    if not account_name or not account_secret:
        sys.exit(1)
    blob_permission = BlobSasPermissions(read=True)
    url = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=account_secret,
        expiry=datetime.utcnow() + timedelta(days=365),
        permission=blob_permission)
    prefix = f"https://{account_name}.blob.core.windows.net"
    return f"{prefix}/{container}/{blob_name}?{url}"


def kusto_client(source: bool):
    _args = pars_env()
    authority_id = _args.get('AZURE_TENANT_ID')
    origin = "SRC" if source else "DEST"
    cluster = _args.get(f'{origin}_CLUSTER')
    client_id = _args.get('MIGRATION_CLIENT_ID')
    client_secret = _args.get('MIGRATION_CLIENT_SECRET')
    kcsb_client = Kusto.with_aad_application_key_authentication(
        cluster, client_id, client_secret, authority_id)
    return kcsb_client


def pass_kusto_mgmt_client(
        func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _args = pars_env()
        authority_id = _args.get('AZURE_TENANT_ID')
        azure_subscription = _args.get('AZURE_SUBSCRIPTION_ID')
        client_id = _args.get('MIGRATION_CLIENT_ID')
        client_secret = _args.get('MIGRATION_CLIENT_SECRET')
        credential = ClientSecretCredential(client_id=client_id,
                                            tenant_id=authority_id,
                                            client_secret=client_secret)
        kcsb_client = KustoManagementClient(
            credential=credential, subscription_id=azure_subscription
        )
        kwargs["mgmt"] = kcsb_client
        return func(*args, **kwargs)
    return wrapper


def pass_blob_client(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        _args = pars_env()
        account_name = _args.get('ACCOUNT_EXPORT_NAME')
        account_secret = _args.get('ACCOUNT_EXPORT_SECRET')
        prefix = f"DefaultEndpointsProtocol=https;AccountName={account_name}"
        suffix = "EndpointSuffix=core.windows.net"
        c_str = f"{prefix};AccountKey={account_secret};{suffix}"
        blob_client = BlobServiceClient.from_connection_string(c_str)
        kwargs["export_blob_client"] = blob_client
        return func(*args, **kwargs)
    return wrapper


# FUNCTIONS #
def create_external_tables_in_source_database(
    database: str,
):
    print(f"-- Create external tables in database {database} --")
    _args = pars_env()
    account_name = _args.get('ACCOUNT_EXPORT_NAME')
    account_secret = _args.get('ACCOUNT_EXPORT_SECRET')
    results = []
    src_kcsb_client = kusto_client(source=True)
    with KustoClient(src_kcsb_client) as client_source:
        query = ".show tables"
        res = None
        try:
            res = client_source.execute_mgmt(database, query)
        except Exception:
            pass
        if not res:
            return results
        data = res.primary_results[0].to_dict()
        for row in data['data']:
            tb = row['TableName']
            table_name = str(tb).lower()
            id = uuid4()
            tb_final = f"csm-{id}-{database}".lower()[:63]
            query = f".show table ['{tb}'] kqlschema"
            sch = client_source.execute_mgmt(database, query)
            data = sch.primary_results[0].to_dict()
            s = data['data'][0]['Schema']
            query = f"""
.create external table csm{table_name} ({s})
kind=blob
dataformat=csv
(
    h@'https://{account_name}.blob.core.windows.net/{tb_final};{account_secret}'
)
"""
            try:
                response = client_source.execute_mgmt(database, query)
                if not response:
                    continue
                data = response.primary_results[0].to_dict()
                for t in data['data']:
                    print(f"{t['TableName']} created")
                    results.append({"id": tb_final, "table": tb})
            except Exception:
                print(f"Ext. table {table_name} already exists in {database}")
                continue
        return results


def export_data_to_external_storage(
    database: str,
):
    print("-- Export data to external table --")
    results = []
    src_kcsb_client = kusto_client(source=True)
    with KustoClient(src_kcsb_client) as client_source:
        query = """.show tables"""
        try:
            tables = client_source.execute_mgmt(database, query)
            data = tables.primary_results[0].to_dict()
            for row in data['data']:
                tb = row['TableName']
                table_name = str(tb).lower()
                query = f"""
.export to table csm{table_name} with (
    sizeLimit=1000000000,
    includeHeaders="firstFile"
) <| ['{tb}']
"""
                try:
                    response = client_source.execute_mgmt(database, query)
                    data = response.primary_results[0].to_dict()
                    results.append(f"csm{table_name}")
                    print(f"table successfully exported csm{table_name}")
                except Exception as exp:
                    print(f"table csm{table_name} error: {exp}")
        except Exception as exp:
            print(exp)
    return results


def get_schema_as_csl(
    database: str
) -> list:
    print("-- Get schema database as csl script from adx --")
    scripts = []
    src_kcsb_client = kusto_client(source=True)
    with KustoClient(src_kcsb_client) as client_source:
        query = """
.show database schema as csl script with (ShowObfuscatedStrings = true)"""
        try:
            tables = client_source.execute_mgmt(database, query)
            data = tables.primary_results[0].to_dict()
            for item in data['data']:
                item = item['DatabaseSchemaScript']
                scripts.append(item)
        except Exception as exp:
            print(exp)
            pass
        return scripts


def drop_external_table(
    database: str,
    table_name: str
):
    print("-- Drop external table in adx --")
    src_kcsb_client = kusto_client(source=True)
    with KustoClient(src_kcsb_client) as client_source:
        query = f""".drop external table ['{table_name}']"""
        tables = client_source.execute_mgmt(database, query)
        data = tables.primary_results[0].to_dict()
        for t in data['data']:
            print(t['TableName'])


def get_external_tables(
    database: str,
):
    print("-- Get external tables list from adx --")
    external_tables = []
    src_kcsb_client = kusto_client(source=True)
    with KustoClient(src_kcsb_client) as client_source:
        query = """.show external tables"""
        try:
            tables = client_source.execute_mgmt(database, query)
            if not tables:
                return external_tables
            data = tables.primary_results[0].to_dict()
            for t in data['data']:
                external_tables.append(t['TableName'])
        except Exception as exp:
            print(exp)
            return external_tables
    return external_tables


def clone_database(
    database: str,
    list_scripts: list
) -> bool:
    print(f"-- Clone schemas database {database}--")
    dest_kcsb_client = kusto_client(source=False)
    with KustoClient(dest_kcsb_client) as client_dest:
        if not len(list_scripts):
            return False
        for query in list_scripts:
            try:
                result = client_dest.execute_mgmt(database, query)
                if not result:
                    continue
            except Exception as exp:
                print(exp)
                continue


def ingest_data(
    database: str,
    table: str,
    sas: str
) -> bool:
    print("-- Ingest data --")
    dest_kcsb_client = kusto_client(source=False)
    with KustoClient(dest_kcsb_client) as client_dest:
        try:
            if sas:
                query = f"""
.ingest into table {table}
(
    {sas}
)
"""
                print(query)
                response = client_dest.execute_mgmt(database, query)
                if not response:
                    return False
                data = response.primary_results[0].to_dict()
                for d in data['data']:
                    if d['HasErrors']:
                        sys.exit(1)
                return True
        except Exception as exp:
            print(f"Error: {exp}")
            return False


@pass_blob_client
def get_list_container_ext_tables(
    export_blob_client: BlobServiceClient,
    database: str
):
    print("-- Get external table list from storage account --")
    results = []
    containers = export_blob_client.list_containers(
        name_starts_with=f"csm-{database}-".lower()
    )
    for c in containers:
        results.append(c['name'])
    return results


def get_tables_from_adx(
    database: str,
):
    print("-- Get table list database adx --")
    results = []
    dest_kcsb_client = kusto_client(source=False)
    with KustoClient(dest_kcsb_client) as client_dest:
        query = """.show tables"""
        response = client_dest.execute_mgmt(database, query)
        data = response.primary_results[0].to_dict()
        for t in data['data']:
            results.append(t['TableName'])
    return results


@pass_blob_client
def save_history(
    export_blob_client: BlobServiceClient,
    data: dict,
    database: str
):
    blob_client = export_blob_client.get_blob_client(
        container="export-history",
        blob=f"csmstate{database}"
    )
    if blob_client.exists():
        blob_client.delete_blob()
    yaml_file = yaml.dump(data)
    blob_client.upload_blob(yaml_file)


@pass_blob_client
def retrieve_state(
    export_blob_client: BlobServiceClient,
    database: str
) -> dict:
    state_name = f"csmstate{database}"
    try:
        blob_client = export_blob_client.get_blob_client(
            container="export-history",
            blob=state_name
        )
        data = dict()
        if blob_client.exists():
            state = blob_client.download_blob()
            yaml_state = yaml.load(state.read(), Loader=yaml.SafeLoader)
            return yaml_state
    except Exception:
        pass
    steps = []
    steps.append(dict(
        name="create_external_tables",
        tables=list(),
        state=None))
    steps.append(dict(
        name="export_data_to_tables",
        tables=list(),
        state=None))
    steps.append(dict(
        name="drop_external_tables",
        tables=list(),
        state=None))
    steps.append(dict(
        name="clone_database_scheme",
        scripts=list(),
        state=None))
    steps.append(dict(
        name="ingest_data",
        tables=list(),
        state=None))
    data.setdefault("steps", steps)
    data.setdefault("start", None)
    data.setdefault("database", None)
    return data


def export(
    data: dict,
    database: str
):
    if data['steps'][0]['state'] is True:
        print("Skipping external table")
    if data['steps'][0]['state'] is None:
        print("step 0")
        ext_tables = create_external_tables_in_source_database(
            database=database
        )
        data['steps'][0]['tables'] = ext_tables
        data['steps'][0]['state'] = True
        save_history(data=data, database=database)

    if data['steps'][1]['state'] is True:
        print("Skipping export table")
    if data['steps'][1]['state'] is None:
        print("step 1")
        exported_tables = export_data_to_external_storage(
            database=database
        )
        data['steps'][1]['tables'] = exported_tables
        data['steps'][1]['state'] = True
        save_history(data=data, database=database)

    if data['steps'][2]['state'] is True:
        print("Skipping drop external table")
    if data['steps'][2]['state'] is None:
        print("step 2")
        ext_tables = get_external_tables(
            database=database
        )
        for item in ext_tables:
            drop_external_table(
                database=database,
                table_name=item
            )
        data['steps'][2]['tables'] = ext_tables
        data['steps'][2]['state'] = True
        save_history(data=data, database=database)


@pass_blob_client
def ingest(
    export_blob_client: BlobServiceClient,
    database: str,
    data: dict,
    ext_table: str,
    container: str
) -> bool:
    imported_tables = data['steps'][4]['tables']
    try:
        if container in imported_tables:
            return False
        container_client = export_blob_client.get_container_client(
            container=container
        )
        if not container_client.exists():
            return False
        blobs = container_client.list_blobs()
        for b in blobs:
            sas = generate_sas_token(
                blob_name=b['name'],
                container=container
            )
            query = f"h'{sas}'"
            ingested = ingest_data(
                database=database,
                table=ext_table,
                sas=query
            )
            if ingested:
                c_b = export_blob_client.get_blob_client(
                    container=container,
                    blob=b
                )
                c_b.delete_blob()
            time.sleep(2)
        container_client.delete_container()
        print(f"container {container} deleted")
        imported_tables.append(container)
        ext_tables = data['steps'][1]['tables']
        data['steps'][4]['tables'] = imported_tables
        data['steps'][4]['state'] = len(ext_tables) == (len(imported_tables))
        save_history(data=data, database=database)
        return True
    except Exception as exp:
        print(exp)


def clone(data: dict, database: str):
    list_scripts = get_schema_as_csl(
        database=database
    )
    ok = clone_database(
        database=database,
        list_scripts=list_scripts
    )
    data['steps'][3]['scripts'] = list_scripts
    data['steps'][3]['state'] = ok
    save_history(data=data, database=database)
    return ok


@pass_kusto_mgmt_client
def create_kusto_database_in_dest(
    mgmt: KustoManagementClient,
    database: str,
):
    args = pars_env()
    resource_group_name = args.get('DEST_RESOURCE_GROUP')
    cluster_name, resource_location = get_cluster_values(source=False)
    params_database = ReadWriteDatabase(location=resource_location,
                                        soft_delete_period=timedelta(days=365),
                                        hot_cache_period=timedelta(days=31))
    try:
        name_request = CheckNameRequest(
            name=database, type="Microsoft.Kusto/clusters/databases")
        mgmt.databases.check_name_availability(
            resource_group_name=resource_group_name,
            cluster_name=cluster_name,
            resource_name=name_request,
            content_type="application/json")
    except Exception as exp:
        print(exp)
    _ret: list[str] = []
    poller = mgmt.databases.begin_create_or_update(
        resource_group_name=resource_group_name,
        cluster_name=cluster_name,
        database_name=database,
        parameters=params_database,
        content_type="application/json")
    poller.wait()
    if poller.done():
        print("\n".join(_ret))


@pass_kusto_mgmt_client
def iam_set(
    mgmt: KustoManagementClient,
    database: str
):
    args = pars_env()
    principal_id = args.get('MIGRATION_CLIENT_ID')
    resource_group_name = args.get('SRC_RESOURCE_GROUP')
    cluster_name, location = get_cluster_values(source=False)
    parameters = DatabasePrincipalAssignment(
        principal_id=principal_id,
        principal_type="App", role="Admin")
    principal_assignment_name = str(uuid4())
    try:
        poller = mgmt.database_principal_assignments.begin_create_or_update(
            resource_group_name, cluster_name,
            database,
            principal_assignment_name, parameters)
        if poller.done():
            print("Successfully created")
    except Exception:
        print("Exception: Already exists with the same role and principal id")


@pass_blob_client
def init(
    export_blob_client: BlobServiceClient
):
    try:
        container_client = export_blob_client.get_container_client(
            container="export-history"
        )
        if not container_client.exists():
            container_client.create_container()
    except Exception as exp:
        print(exp)
        sys.exit(1)


@pass_kusto_mgmt_client
def check_database_in_src(
    mgmt: KustoManagementClient,
    database: str
) -> bool:
    args = pars_env()
    try:
        rg = args.get('SRC_RESOURCE_GROUP')
        cluster_name, _ = get_cluster_values(source=True)
        mgmt.databases.get(
            resource_group_name=rg,
            cluster_name=cluster_name,
            database_name=database
        )
        return True
    except Exception:
        return False


@pass_kusto_mgmt_client
def check_database_in_dest(
    mgmt: KustoManagementClient,
    database: str
) -> bool:
    args = pars_env()
    try:
        rg = args.get('DEST_RESOURCE_GROUP')
        cluster_name, _ = get_cluster_values(source=False)
        mgmt.databases.get(
            resource_group_name=rg,
            cluster_name=cluster_name,
            database_name=database
        )
        return True
    except Exception:
        return False


def get_cluster_values(source: bool):
    args = pars_env()
    origin = "SRC" if source else "DEST"
    cluster = args.get(f"{origin}_CLUSTER")
    rx101 = 'https:\\/\\/([a-zA-Z0-9].+)\\.([a-zA-Z0-9].+).kusto.+'
    results = re.search(rx101, cluster)
    adx_cluster_name, resource_location = results.groups()
    return adx_cluster_name, resource_location


def run_kusto(body: BodyKusto):
    init()
    databases = body.databases
    steps = list(filter(lambda x: x, body.steps))
    for db in databases:
        if db == "" or not isinstance(db, str):
            continue
        db_str: str = db
        db = db_str.replace("\n", "")
        print(f"working with database: {db}")
        data: dict = retrieve_state(database=db)
        data.update({"start": time.time()})
        data.update({"database": db})
        ok = check_database_in_src(database=db)
        if not ok:
            print(f"{db} database not found")
            continue
        if '--kusto-iam' in steps:
            iam_set(database=db)
        if '--kusto-create' in steps:
            ok = check_database_in_dest(database=db)
            if ok:
                print(f"{db} already exists")
            else:
                create_kusto_database_in_dest(database=db)
                print("successfully created")
        if '--kusto-export' in steps:
            export(data=data, database=db)
            print("successfully exported")
        if '--kusto-clone' in steps:
            ok = check_database_in_dest(database=db)
            if not ok:
                print(f"{db} not created yet")
                print("please add --kusto-create flag in steps")
                continue
            ok = clone(data=data, database=db)
            if not ok:
                continue
            print("successfully cloned")
        if '--kusto-ingest' in steps:
            if not data['steps'][3]['state']:
                print(f"database {db} not cloned yet")
                print("please add --kusto-clone")
                continue
            dictionary_tables = data['steps'][0]['tables']
            for item in dictionary_tables:
                try:
                    ok = ingest(
                        database=db,
                        data=data,
                        ext_table=item.get('table'),
                        container=item.get('id')
                    )
                    if ok:
                        print("successfully ingested")
                except Exception:
                    continue
