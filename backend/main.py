from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

from app.schemas.music_video import (
    MusicVideoPlanRequest,
    MusicVideoPlanResponse,
    MusicVideoSourcesResponse,
)
from app.services.music_video_generator import MusicVideoPlanner
from .models import OpenPoint, OpenPointCreate, Status

app = FastAPI()
music_video_planner = MusicVideoPlanner()

# Allow CORS for the frontend
origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite's default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database
db: Dict[int, OpenPoint] = {}
id_counter = 0

@app.get("/")
def read_root():
    return {
        "message": "A2A music video planning backend",
        "routes": [
            "/music-video/sources",
            "/music-video/plan",
            "/open-points",
        ],
    }

@app.get("/open-points", response_model=List[OpenPoint])
def get_open_points():
    return list(db.values())

@app.post("/open-points", response_model=OpenPoint)
def create_open_point(open_point: OpenPointCreate):
    global id_counter
    id_counter += 1
    new_point = OpenPoint(id=id_counter, **open_point.dict())
    db[id_counter] = new_point
    return new_point

@app.get("/open-points/{point_id}", response_model=OpenPoint)
def get_open_point(point_id: int):
    if point_id not in db:
        raise HTTPException(status_code=404, detail="Open point not found")
    return db[point_id]

@app.put("/open-points/{point_id}", response_model=OpenPoint)
def update_open_point_status(point_id: int, status: Status):
    if point_id not in db:
        raise HTTPException(status_code=404, detail="Open point not found")
    db[point_id].status = status
    return db[point_id]

class ExecutionRequest(BaseModel):
    code: str

class ExecutionResponse(OpenPoint):
    output: str
    exit_code: int

@app.post("/execute/{point_id}", response_model=ExecutionResponse)
def execute_task(point_id: int, request: ExecutionRequest):
    if point_id not in db:
        raise HTTPException(status_code=404, detail="Open point not found")

    point = db[point_id]
    point.status = Status.IN_PROGRESS

    # NOTE: This is where the sandboxed execution will happen.
    # For now, we'll just simulate it.
    print(f"Executing code for task {point_id}:\n{request.code}")

    # Simulate execution
    output = "Simulated execution output."
    exit_code = 0

    point.status = Status.DONE if exit_code == 0 else Status.ERROR

    return ExecutionResponse(
        **point.dict(),
        output=output,
        exit_code=exit_code,
    )


@app.get("/music-video/sources", response_model=MusicVideoSourcesResponse)
def get_music_video_sources() -> MusicVideoSourcesResponse:
    return music_video_planner.get_sources_response()


@app.post("/music-video/plan", response_model=MusicVideoPlanResponse)
def create_music_video_plan(request: MusicVideoPlanRequest) -> MusicVideoPlanResponse:
    return music_video_planner.plan(request)
