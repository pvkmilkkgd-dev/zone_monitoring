from fastapi import FastAPI

app = FastAPI(title="Debug App")


@app.get("/ping")
def ping():
    return {"status": "ok"}
