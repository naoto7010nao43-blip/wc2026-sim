from fastapi import APIRouter

from app.schemas.data_quality import DataQualitySummary
from app.services.data_quality import compute_data_quality_summary

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/summary", response_model=DataQualitySummary)
def get_data_quality_summary():
    return compute_data_quality_summary()
