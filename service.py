from uvicorn import run
from multiprocessing import Process
from multiprocessing import set_start_method
from fastapi import FastAPI, Request
from common import BodyKusto, BodyStorage
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
    p = Process(target=run_storage, args=(body,))
    p.start()
    return {"result": body}


@app.post("/kustos")
def kusto(request: Request, body: BodyKusto):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    p = Process(target=run_kusto, args=(body,))
    p.start()
    return {"result": body}


@app.post("/kustos/test")
def kustotest(request: Request, body: BodyKusto):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    databases = body.databases
    for db in databases:
        tables_dest = get_dest_tables_from_adx(
            database=db
        )
        _ret = []
        for t in tables_dest:
            rows_dest = count_dest_table(database=db, table=t)
            rows_src = count_src_table(database=db, table=t)
            if rows_dest[0]-rows_src[0]:
                _ret.append(f"{t} diff {rows_dest[0]-rows_src[0]}")
    return {"result": _ret}


@app.patch("/solutions")
def solution(request: Request):
    if "Csm-Key" not in request.headers:
        return {"error": "csm-key"}
    client = CsmJsonRedisClient()
    solutions = handler(client)
    return solutions


if __name__ == "__main__":
    set_start_method("spawn")
    run(app=app)
