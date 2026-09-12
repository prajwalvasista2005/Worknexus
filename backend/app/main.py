from fastapi import FastAPI
from app.api.auth import router as auth_router

app=FastAPI(
    title="SkillSync",
    version="1.0.0"
)
app.include_router(auth_router)
@app.get("/")
def read_root():
    return {"message":"SkillSync is up and running!"}