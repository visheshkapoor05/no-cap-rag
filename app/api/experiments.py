"""T-M4.12: GET /experiments/{id} and POST /experiments/compare -- the
read side of T-M4.11's experiment persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.db import get_pool
from app.evaluation import compare_experiments, get_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentResponse(BaseModel):
    id: UUID
    name: str
    config: dict[str, Any]
    dataset_version: str
    embedding_model: str
    reranker_model: str | None
    llm_model: str
    metrics: dict[str, Any]
    created_at: datetime


class CompareResponse(BaseModel):
    a: ExperimentResponse
    b: ExperimentResponse
    diff: dict[str, float]


def _to_response(exp) -> ExperimentResponse:
    return ExperimentResponse(
        id=exp.id, name=exp.name, config=exp.config, dataset_version=exp.dataset_version,
        embedding_model=exp.embedding_model, reranker_model=exp.reranker_model,
        llm_model=exp.llm_model, metrics=exp.metrics, created_at=exp.created_at,
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment_by_id(experiment_id: UUID) -> ExperimentResponse:
    pool = get_pool()
    exp = get_experiment(pool, experiment_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"no experiment with id {experiment_id}")
    return _to_response(exp)


class CompareRequest(BaseModel):
    id_a: UUID
    id_b: UUID


@router.post("/compare", response_model=CompareResponse)
def compare(request: CompareRequest) -> CompareResponse:
    pool = get_pool()
    try:
        result = compare_experiments(pool, request.id_a, request.id_b)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return CompareResponse(a=_to_response(result["a"]), b=_to_response(result["b"]), diff=result["diff"])
