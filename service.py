import os
from uvicorn import run
from fastapi import FastAPI, Request
from common import BodyKusto, BodyKustoTest, BodyStorage
from kusto import run_kusto
from kusto_test import count_dest_table
from kusto_test import count_src_table
from kusto_test import get_dest_tables_from_adx
from solution import CsmJsonRedisClient
from solution import handler
from storage import run_storage

app = FastAPI()


@app.post("/storages")
def storage(request: Request, body: BodyStorage):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    if request.headers["Csm-Key"] != os.environ.get("CSM_KEY"):
        return {"error": "csm-key"}
    run_storage(body)
    return {"result": "OK"}


@app.post("/kustos")
def kusto(request: Request, body: BodyKusto):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    if request.headers["Csm-Key"] != os.environ.get("CSM_KEY"):
        return {"error": "csm-key"}
    run_kusto(body)
    return {"result": "OK"}


@app.post("/kustos/test")
def kustotest(request: Request, body: BodyKustoTest):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    if request.headers["Csm-Key"] != os.environ.get("CSM_KEY"):
        return {"error": "csm-key"}
    if not len(body.databases):
        return {"result": None}
    databases = body.databases
    for db in databases:
        tables_dest = get_dest_tables_from_adx(database=db)
        _ret = []
        for t in tables_dest:
            rows_dest = count_dest_table(database=db, table=t)
            rows_src = count_src_table(database=db, table=t)
            if rows_dest[0] - rows_src[0]:
                _ret.append(f"{t} dif {rows_dest[0]-rows_src[0]}")
        if not len(_ret):
            print(f"Successfully migrated: {db}")
    return {"result": _ret}


@app.patch("/solutions")
def solution(request: Request):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    if request.headers["Csm-Key"] != os.environ.get("CSM_KEY"):
        return {"error": "csm-key"}
    client = CsmJsonRedisClient()
    solutions = handler(client)
    return {"result": solutions}


if __name__ == "__main__":
    run(app=app)
