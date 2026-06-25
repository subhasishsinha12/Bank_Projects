from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database.seed import seed_all
from models.credit_model import load_model
from routers import viveka, raksha, satya


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_all()
    load_model()
    yield


app = FastAPI(
    title="DRISHTI API",
    description="Digital Risk Intelligence & Scrutiny Hub for Transparent Intelligence — IDBI Innovate 2026",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(viveka.router)
app.include_router(raksha.router)
app.include_router(satya.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
