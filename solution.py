import os
import redis
import json

from pydantic import BaseModel
from redis.commands.search.query import Query


class CSMSolution(BaseModel):
    Id: str
    Key: str
    Name: str
    Description: str
    Respository: str
    Csmsimulator: str
    Version: str
    OwnerId: str
    SdkVersion: str
    url: str
    organizationId: str
    runTemplates: list


def CsmJsonRedisClient():
    client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=os.environ.get('REDIS_PORT', 6379),
        username=os.environ.get('REDIS_USERNAME', ''),
        password=os.environ.get('REDIS_PASSWORD', ''),
        db=0
    )
    return client


def CsmJsonGet(client: redis.Redis, key: str):
    solution = client.json().get(key)
    return solution


def CsmJsonSet(client: redis.Redis, key: str, solution: CSMSolution):
    client.json().set(name=key, path=".", obj=solution)


def CsmGetAllSolutions(client: redis.Redis) -> list[dict]:
    total = 0
    q_total = Query("*").paging(0, 0)
    total = client.ft("com.cosmotech.solution.domain.SolutionIdx").search(
        query=q_total).total
    q_all = Query("*").paging(0, total)
    sol_docs = client.ft("com.cosmotech.solution.domain.SolutionIdx").search(
        query=q_all
    ).docs
    sols: list[dict] = [json.loads(doc.json) for doc in sol_docs]
    return sols


def handlerRunTemplatesCsmOrcWithMinus(sol: dict):
    rts = sol['runTemplates']
    for i, item in enumerate(rts):
        if "csmMinusOrc" in item["orchestratorType"]:
            rts[i]['orchestratorType'] = "csmOrc"
        if "argoMinusWorkflow" in item["orchestratorType"]:
            rts[i]['orchestratorType'] = "argoWorkflow"


def handlerRunTemplatesCsmOrcWithSteps(sol: dict):
    rts: list = sol["runTemplates"]
    for i, item in enumerate(rts):
        if item["orchestratorType"] == "":
            rts[i]['orchestratorType'] == "argoWorkflow"
        if item["fetchDatasets"] is None:
            rts[i]['fetchDatasets'] = True
        if item["fetchScenarioParameters"] is None:
            rts[i]['fetchScenarioParameters'] = True
        if item["applyParameters"] is None:
            rts[i]['applyParameters'] = True
        if item["sendDatasetsToDataWarehouse"] is None:
            rts[i]['sendDatasetsToDataWarehouse'] = True
        if item["sendInputParametersToDataWarehouse"] is None:
            rts[i]['sendInputParametersToDataWarehouse'] = True
        if item["preRun"] is None:
            rts[i]['preRun'] = True
        if item["run"] is None:
            rts[i]['run'] = True
        if item["postRun"] is None:
            rts[i]['postRun'] = True

    new_sol = sol["runTemplates"] = rts
    return new_sol


def handler(client: redis.Redis):
    solutions = []
    try:
        solutions = CsmGetAllSolutions(client)
    except Exception as exp:
        print(exp)
        return solutions
    for sol in solutions:
        new_sol = handlerRunTemplatesCsmOrcWithSteps(sol)
        new_sol = handlerRunTemplatesCsmOrcWithMinus(sol)
        CsmJsonSet(client, sol['id'], new_sol)
    print("Successfully Completed")
    return solutions
