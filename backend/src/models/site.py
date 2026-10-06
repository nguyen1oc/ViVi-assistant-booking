from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SiteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Media(SiteModel):
    url: str
    alt: str = ""
    focal_point: str | None = Field(default=None, alias="focalPoint")


class StudioImage(SiteModel):
    url: str
    mode: str


class ShortSpec(SiteModel):
    label: str
    value: str


class VehicleSummary(SiteModel):
    id: str
    name: str
    nav_name: str = Field(alias="navName")
    category: str
    body_type: str = Field(alias="bodyType")
    seats: int
    display_price: str = Field(alias="displayPrice")
    tagline: str
    thumbnail: Media
    studio_image: StudioImage = Field(alias="studioImage")
    short_specs: list[ShortSpec] = Field(alias="shortSpecs")
    featured: bool
    test_drive_eligible: bool = Field(alias="testDriveEligible")
    sort_order: int = Field(alias="sortOrder")
    revision: str
    range: dict[str, Any] | None = None
    charging: dict[str, Any] | None = None
    color_options: list[dict[str, Any]] | None = Field(default=None, alias="colorOptions")


class VehicleDetail(VehicleSummary):
    description: str
    brochure: dict[str, Any]
    specifications: list[dict[str, Any]]
    colors: list[dict[str, Any]]
    chapters: list[dict[str, Any]]
    gallery: list[dict[str, Any]]
    presentation_film: dict[str, Any] | None = Field(alias="presentationFilm")
    motion: dict[str, Any]


class ResponseMeta(SiteModel):
    request_id: str = Field(alias="requestId")
    server_time: str = Field(alias="serverTime")


DataT = TypeVar("DataT")


class DataEnvelope(SiteModel, Generic[DataT]):
    data: DataT
    meta: ResponseMeta


class ErrorBody(SiteModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(SiteModel):
    error: ErrorBody
    meta: ResponseMeta


class ContentDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    revision: str


class CatalogSnapshot(SiteModel):
    vehicles: list[VehicleSummary]
    details: dict[str, dict[str, Any]]
    content: dict[str, ContentDocument]

    @model_validator(mode="after")
    def require_home_testimonials(self) -> "CatalogSnapshot":
        home = self.content.get("home")
        testimonials = home.model_dump().get("testimonials") if home else None
        if not isinstance(testimonials, list) or not testimonials:
            raise ValueError("Home content must include at least one published testimonial")
        return self
