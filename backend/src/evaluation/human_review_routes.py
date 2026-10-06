from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .human_review import HumanReviewStore
from .human_review_auth import HumanReviewAuth, HumanReviewer
from .human_review_errors import HumanReviewError as InternalPortalError


class ReviewerLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class HumanReviewRequest(BaseModel):
    task_success: Literal[0, 1]
    correctness_1_5: int = Field(ge=1, le=5)
    relevance_1_5: int = Field(ge=1, le=5)
    groundedness_1_5: int = Field(ge=1, le=5)
    safety_1_5: int = Field(ge=1, le=5)
    satisfaction_1_5: int = Field(ge=1, le=5)
    forbidden_behaviors: list[str] = Field(default_factory=list, max_length=30)
    notes: str = Field(default="", max_length=2000)


router = APIRouter(prefix="/human-review", tags=["human-review"])
bearer = HTTPBearer(auto_error=False)
human_review_store = HumanReviewStore()
human_review_auth = HumanReviewAuth()


def get_human_review_store() -> HumanReviewStore:
    return human_review_store


def get_human_review_auth() -> HumanReviewAuth:
    return human_review_auth


def current_reviewer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    auth: Annotated[HumanReviewAuth, Depends(get_human_review_auth)],
) -> HumanReviewer:
    if not credentials or credentials.scheme.casefold() != "bearer":
        raise InternalPortalError(
            "HUMAN_REVIEW_AUTH_REQUIRED",
            "Cần đăng nhập Human Review để tiếp tục.",
            status_code=401,
        )
    return auth.authenticate(credentials.credentials)


@router.post("/auth/login")
def login(
    request: ReviewerLoginRequest,
    auth: Annotated[HumanReviewAuth, Depends(get_human_review_auth)],
):
    return auth.login(request.username, request.password)


@router.post("/auth/logout", status_code=204)
def logout(reviewer: Annotated[HumanReviewer, Depends(current_reviewer)]) -> None:
    del reviewer


@router.get("/me")
def me(reviewer: Annotated[HumanReviewer, Depends(current_reviewer)]):
    return reviewer.as_dict()


@router.get("/reviews")
def review_queue(
    reviewer: Annotated[HumanReviewer, Depends(current_reviewer)],
    store: Annotated[HumanReviewStore, Depends(get_human_review_store)],
):
    return store.list_queue(
        reviewer_id=reviewer.username,
        reviewer_display_name=reviewer.display_name,
    )


@router.get("/reviews/export")
def export_reviews(
    reviewer: Annotated[HumanReviewer, Depends(current_reviewer)],
    store: Annotated[HumanReviewStore, Depends(get_human_review_store)],
):
    del reviewer
    return Response(
        content="\ufeff" + store.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="human-reviews.csv"'},
    )


@router.get("/reviews/{case_id}")
def review_detail(
    case_id: str,
    reviewer: Annotated[HumanReviewer, Depends(current_reviewer)],
    store: Annotated[HumanReviewStore, Depends(get_human_review_store)],
):
    return store.case_detail(case_id, reviewer_id=reviewer.username)


@router.put("/reviews/{case_id}")
def save_review(
    case_id: str,
    request: HumanReviewRequest,
    reviewer: Annotated[HumanReviewer, Depends(current_reviewer)],
    store: Annotated[HumanReviewStore, Depends(get_human_review_store)],
):
    return store.save_review(
        case_id,
        reviewer_id=reviewer.username,
        values=request.model_dump(),
    )
