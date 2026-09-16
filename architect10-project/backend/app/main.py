"""
API surface for the dubbing pipeline.

Run with:
    uvicorn app.main:app --reload

Then:
    POST   /jobs                       start a job -> {job_id}
    GET    /jobs/{job_id}              poll status
    GET    /jobs/{job_id}/download/{lang}   fetch a finished dubbed file
"""
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import LANGUAGE_NAMES, settings
from app.models import DubJobRequest, JobStatus, LanguageResult, Stage
from app.pipeline.orchestrator import run_dub_job

app = FastAPI(title="Architect 10 Dubbing API")

# Loosen this to your real frontend origin(s) before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, JobStatus] = {}
_executor = ThreadPoolExecutor(max_workers=settings.JOB_CONCURRENCY)


@app.post("/jobs")
def create_job(req: DubJobRequest) -> dict:
    unknown = [l for l in req.languages if l not in LANGUAGE_NAMES]
    if unknown:
        raise HTTPException(400, f"Unsupported language code(s): {unknown}")
    if not req.languages:
        raise HTTPException(400, "Provide at least one target language.")

    job_id = uuid.uuid4().hex[:12]
    job = JobStatus(
        job_id=job_id,
        source_url=req.url,
        languages={code: LanguageResult(language=code) for code in req.languages},
    )
    JOBS[job_id] = job

    _executor.submit(run_dub_job, job_id, JOBS)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str) -> JobStatus:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@app.get("/jobs/{job_id}/download/{lang}")
def download_result(job_id: str, lang: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    result = job.languages.get(lang)
    if not result or result.stage != Stage.DONE or not result.output_path:
        raise HTTPException(404, "That language isn't ready yet.")
    if not Path(result.output_path).exists():
        raise HTTPException(
            410, "That file is no longer on disk (job data may have been cleaned up)."
        )
    return FileResponse(result.output_path, filename=f"{job_id}_{lang}.mp4")


@app.get("/languages")
def list_languages() -> dict:
    return LANGUAGE_NAMES
