from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.skills import router as skills_router
from app.api.courses import router as courses_router
from app.api.user_skills import router as user_skills_router
from app.api.course_skills import router as course_skills_router
from app.api.job_postings import router as job_postings_router
from app.api.job_skills import router as job_skills_router

app = FastAPI(
    title="WorkNexus",
    description="Labour Market Intelligence & Curriculum Alignment Platform API",
    version="1.0.0",
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(skills_router)
app.include_router(courses_router)
app.include_router(user_skills_router)
app.include_router(course_skills_router)
app.include_router(job_postings_router)
app.include_router(job_skills_router)


@app.get("/", tags=["Health"])
def read_root():
    return {
        "status": "healthy",
        "platform": "WorkNexus",
        "version": "1.0.0",
        "message": "WorkNexus Labour Market Intelligence API is up and running!",
    }