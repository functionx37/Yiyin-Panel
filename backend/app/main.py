from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import settings
from .data_access import (
    DataAccessError,
    group_summary,
    list_foods,
    list_quotes,
    list_toggle_groups,
    resolve_food_image,
    resolve_quote_image,
    update_toggle,
    update_food,
)
from .schemas import (
    DebugGroupListResponse,
    FoodsResponse,
    FoodItem,
    FoodUpdateRequest,
    GroupSummaryResponse,
    LoginRequest,
    LoginResponse,
    QuotesResponse,
    ToggleGroup,
    ToggleListResponse,
    ToggleUpdateRequest,
)
from .tokens import build_group_token, create_admin_token, end_of_day, verify_admin_token, verify_group_token

app = FastAPI(title='Yiyin-Panel API', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(DataAccessError)
async def handle_data_error(_, exc: DataAccessError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={'detail': str(exc)},
    )


def _extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='请先登录管理员后台。')
    token = authorization.removeprefix('Bearer ').strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='请先登录管理员后台。')
    return token


def require_admin(token: str = Depends(_extract_bearer_token)) -> dict:
    return verify_admin_token(token)


def require_group_token(group_id: str, token: str = Query(default='')) -> str:
    if not verify_group_token(group_id, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='链接已失效或 token 无效。')
    return token


def _query_with_token(token: str) -> str:
    return urlencode({'token': token})


@app.get(f'{settings.api_base_path}/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post(f'{settings.api_base_path}/admin/login', response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='ADMIN_PASSWORD 未配置。',
        )
    if payload.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='密码错误。')
    token, expires_at = create_admin_token()
    return LoginResponse(access_token=token, expires_at=expires_at.isoformat())


@app.get(
    f'{settings.api_base_path}/admin/toggles',
    response_model=ToggleListResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_toggles() -> ToggleListResponse:
    return ToggleListResponse.model_validate(list_toggle_groups())


@app.get(
    f'{settings.api_base_path}/admin/groups',
    response_model=DebugGroupListResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_groups() -> DebugGroupListResponse:
    debug_groups = []
    toggle_groups = list_toggle_groups().get('groups', [])

    for group in toggle_groups:
        group_id = group.get('group_id')
        if not isinstance(group_id, str) or not group_id:
            continue

        summary = group_summary(group_id)
        token = build_group_token(group_id)
        debug_groups.append(
            {
                **summary,
                'token': token,
                'preview_path': f"{settings.public_base_path}/groups/{group_id}?{_query_with_token(token)}",
            }
        )

    return DebugGroupListResponse.model_validate({'groups': debug_groups})


@app.patch(
    f'{settings.api_base_path}/admin/toggles/{{group_id}}',
    response_model=ToggleGroup,
    dependencies=[Depends(require_admin)],
)
async def patch_toggle(group_id: str, payload: ToggleUpdateRequest) -> ToggleGroup:
    return ToggleGroup.model_validate(update_toggle(group_id, payload.feature_name, payload.enabled))


@app.get(f'{settings.api_base_path}/public/groups/{{group_id}}/summary', response_model=GroupSummaryResponse)
async def public_summary(group_id: str, token: str = Depends(require_group_token)) -> GroupSummaryResponse:
    summary = group_summary(group_id)
    summary['expires_at'] = end_of_day().isoformat()
    return GroupSummaryResponse.model_validate(summary)


@app.get(f'{settings.api_base_path}/public/groups/{{group_id}}/quotes', response_model=QuotesResponse)
async def public_quotes(group_id: str, token: str = Depends(require_group_token)) -> QuotesResponse:
    quote_groups = []
    for member_group in list_quotes(group_id):
        entries = []
        for entry in member_group['entries']:
            item = {
                'id': entry['id'],
                'image_url': (
                    f"{settings.api_base_path}/public/groups/{group_id}/quotes/{entry['id']}/image?{_query_with_token(token)}"
                ),
                'image_width': entry.get('image_width'),
                'image_height': entry.get('image_height'),
                'content': entry.get('content'),
                'speaker_name': entry.get('speaker_name'),
                'avatar_url': entry.get('avatar_url'),
            }
            entries.append(item)

        quote_groups.append(
            {
                'member': member_group['member'],
                'entries': entries,
            }
        )
    return QuotesResponse.model_validate(
        {
            'group_id': group_id,
            'group_name': group_summary(group_id)['group_name'],
            'quote_groups': quote_groups,
        }
    )


@app.get(f'{settings.api_base_path}/public/groups/{{group_id}}/foods', response_model=FoodsResponse)
async def public_foods(group_id: str, token: str = Depends(require_group_token)) -> FoodsResponse:
    items = []
    for item in list_foods(group_id):
        items.append(
            {
                'id': item['id'],
                'name': item['name'],
                'tags': item['tags'],
                'image_url': f"{settings.api_base_path}/public/groups/{group_id}/foods/{item['id']}/image?{_query_with_token(token)}",
                'image_width': item.get('image_width'),
                'image_height': item.get('image_height'),
            }
        )
    return FoodsResponse.model_validate(
        {
            'group_id': group_id,
            'group_name': group_summary(group_id)['group_name'],
            'items': items,
        }
    )


@app.patch(f'{settings.api_base_path}/public/groups/{{group_id}}/foods/{{food_id}}', response_model=FoodItem)
async def patch_food(group_id: str, food_id: str, payload: FoodUpdateRequest, token: str = Depends(require_group_token)) -> FoodItem:
    updated = update_food(group_id, food_id, payload.name, payload.tags)
    updated['image_url'] = f"{settings.api_base_path}/public/groups/{group_id}/foods/{food_id}/image?{_query_with_token(token)}"
    return FoodItem.model_validate(updated)


@app.get(f'{settings.api_base_path}/public/groups/{{group_id}}/quotes/{{quote_id}}/image')
async def quote_image(group_id: str, quote_id: str, _: str = Depends(require_group_token)) -> FileResponse:
    return FileResponse(resolve_quote_image(group_id, quote_id))


@app.get(f'{settings.api_base_path}/public/groups/{{group_id}}/foods/{{food_id}}/image')
async def food_image(group_id: str, food_id: str, _: str = Depends(require_group_token)) -> FileResponse:
    return FileResponse(resolve_food_image(group_id, food_id))
