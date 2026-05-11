from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    expires_at: str


class ToggleUpdateRequest(BaseModel):
    feature_name: str
    enabled: bool


class ToggleItem(BaseModel):
    name: str
    enabled: bool


class FeatureGroup(BaseModel):
    name: str
    members: list[str]


class ToggleGroup(BaseModel):
    group_id: str
    group_name: str
    toggles: list[ToggleItem]


class ToggleListResponse(BaseModel):
    feature_groups: list[FeatureGroup]
    groups: list[ToggleGroup]


class DebugGroupItem(BaseModel):
    group_id: str
    group_name: str
    quote_member_count: int
    quote_count: int
    food_count: int
    token: str
    preview_path: str


class DebugGroupListResponse(BaseModel):
    groups: list[DebugGroupItem]


class GroupSummaryResponse(BaseModel):
    group_id: str
    group_name: str
    quote_member_count: int
    quote_count: int
    food_count: int
    expires_at: str


class QuoteEntry(BaseModel):
    id: str
    image_url: str
    image_width: int | None = None
    image_height: int | None = None
    content: str | None = None
    speaker_name: str | None = None
    avatar_url: str | None = None


class QuoteMemberGroup(BaseModel):
    member: str
    entries: list[QuoteEntry]


class QuotesResponse(BaseModel):
    group_id: str
    group_name: str
    quote_groups: list[QuoteMemberGroup]


class FoodItem(BaseModel):
    id: str
    name: str
    tags: list[str]
    image_url: str
    image_width: int | None = None
    image_height: int | None = None


class FoodUpdateRequest(BaseModel):
    name: str | None = None
    tags: list[str] | None = None


class FoodsResponse(BaseModel):
    group_id: str
    group_name: str
    items: list[FoodItem]
