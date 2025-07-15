from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from backend.service.orchestrator_service import OrchestratorService

app = FastAPI()
orchestrator = OrchestratorService()


@app.post("/api/snapshot")
async def process_snapshot(request: Request):
    """
    Nimmt einen Snapshot als JSON entgegen, verarbeitet ihn und gibt das Ergebnis zurück.
    """
    snapshot = await request.json()
    result_container = {}

    def callback(result=None, errors=None):
        if errors:
            result_container['errors'] = errors
        else:
            result_container['result'] = result

    orchestrator.process_snapshot(snapshot, callback)

    # Warten, bis die Berechnung fertig ist (max. 5 Sekunden)
    import time
    for _ in range(100):
        if result_container:
            break
        time.sleep(0.05)
    if not result_container:
        raise HTTPException(
            status_code=500, detail="Timeout bei der Berechnung")

    if 'errors' in result_container:
        return JSONResponse(status_code=400, content={"errors": result_container['errors']})
    return result_container['result']
