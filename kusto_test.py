from azure.kusto.data import KustoClient
from azure.kusto.data import KustoConnectionStringBuilder as Kusto
from common import pars_env


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


def get_dest_tables_from_adx(
    database: str,
):
    results = []
    dest_kcsb_client = kusto_client(source=False)
    with KustoClient(dest_kcsb_client) as client_dest:
        query = """.show tables"""
        response = client_dest.execute_mgmt(database, query)
        data = response.primary_results[0].to_dict()
        for t in data['data']:
            results.append(t['TableName'])
    return results


def count_dest_table(
    database: str,
    table: str
):
    results = []
    dest_kcsb_client = kusto_client(source=False)
    with KustoClient(dest_kcsb_client) as client_dest:
        query = f"""['{table}'] | count"""
        response = client_dest.execute_query(database, query)
        data = response.primary_results[0].to_dict()
        for t in data['data']:
            results.append(t['Count'])
    return results


def get_src_tables_from_adx(
    database: str,
):
    results = []
    dest_kcsb_client = kusto_client(source=True)
    with KustoClient(dest_kcsb_client) as client_src:
        query = """.show tables"""
        response = client_src.execute_mgmt(database, query)
        data = response.primary_results[0].to_dict()
        for t in data['data']:
            results.append(t['TableName'])
    return results


def count_src_table(
    database: str,
    table: str
):
    results = []
    dest_kcsb_client = kusto_client(source=True)
    with KustoClient(dest_kcsb_client) as client_src:
        query = f"""['{table}'] | count"""
        response = client_src.execute_query(database, query)
        data = response.primary_results[0].to_dict()
        for t in data['data']:
            results.append(t['Count'])
    return results
