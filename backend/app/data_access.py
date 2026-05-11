from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from .config import settings


class DataAccessError(RuntimeError):
    pass


def _require_bot_root() -> Path:
    bot_root = settings.yiyin_bot_path
    if bot_root is None:
        raise DataAccessError("YIYIN_BOT_PATH 未配置。")
    if not bot_root.exists():
        raise DataAccessError(f"YIYIN_BOT_PATH 不存在: {bot_root}")
    return bot_root


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _load_toggle_catalog() -> tuple[list[str], dict[str, bool], list[dict[str, Any]]]:
    bot_root = _require_bot_root()
    toggle_table = _read_json(bot_root / "config" / "toggle_table.json", {})
    default_raw = _read_json(bot_root / "config" / "toggle_default.json", {})

    base_plugin = toggle_table.get("base_plugin", {}) if isinstance(toggle_table, dict) else {}
    feature_order = [value for value in base_plugin.values() if isinstance(value, str)]
    defaults = {
        name: bool(default_raw.get(name)) if isinstance(default_raw, dict) else False
        for name in feature_order
    }

    group_sections: list[dict[str, Any]] = []
    plugin_groups = toggle_table.get("plugin_groups", {}) if isinstance(toggle_table, dict) else {}
    if isinstance(plugin_groups, dict):
        for group_name, members in plugin_groups.items():
            if not isinstance(group_name, str) or not isinstance(members, list):
                continue
            valid_members = [member for member in members if member in feature_order]
            if valid_members:
                group_sections.append({"name": group_name, "members": valid_members})
    return feature_order, defaults, group_sections


def _normalize_toggle_file(group_id: str, raw_data: Any) -> dict[str, Any]:
    feature_order, defaults, _ = _load_toggle_catalog()
    raw_dict = raw_data if isinstance(raw_data, dict) else {}
    raw_toggle = raw_dict.get("toggle", {}) if isinstance(raw_dict.get("toggle"), dict) else {}
    group_name = raw_dict.get("group_name") if isinstance(raw_dict.get("group_name"), str) else group_id
    normalized_toggle = {}
    for feature_name in feature_order:
        value = raw_toggle.get(feature_name)
        normalized_toggle[feature_name] = (
            value if isinstance(value, bool) else defaults.get(feature_name, False)
        )
    return {
        "group_name": group_name or group_id,
        "toggle": normalized_toggle,
    }


def list_toggle_groups() -> dict[str, Any]:
    bot_root = _require_bot_root()
    feature_order, _, feature_groups = _load_toggle_catalog()
    toggle_dir = bot_root / "data" / "toggle"
    groups: list[dict[str, Any]] = []
    for path in sorted(toggle_dir.glob("*.json")):
        group_id = path.stem
        normalized = _normalize_toggle_file(group_id, _read_json(path, {}))
        toggles = [
            {"name": feature_name, "enabled": normalized["toggle"][feature_name]}
            for feature_name in feature_order
        ]
        groups.append(
            {
                "group_id": group_id,
                "group_name": normalized["group_name"] or group_id,
                "toggles": toggles,
            }
        )
    groups.sort(key=lambda item: ((item["group_name"] or item["group_id"]).lower(), item["group_id"]))
    return {"feature_groups": feature_groups, "groups": groups}


def update_toggle(group_id: str, feature_name: str, enabled: bool) -> dict[str, Any]:
    bot_root = _require_bot_root()
    feature_order, _, _ = _load_toggle_catalog()
    if feature_name not in feature_order:
        raise DataAccessError(f"未知功能: {feature_name}")

    toggle_path = bot_root / "data" / "toggle" / f"{group_id}.json"
    normalized = _normalize_toggle_file(group_id, _read_json(toggle_path, {}))
    normalized["toggle"][feature_name] = enabled
    _write_json(toggle_path, normalized)
    return {
        "group_id": group_id,
        "group_name": normalized["group_name"] or group_id,
        "toggles": [
            {"name": name, "enabled": normalized["toggle"][name]}
            for name in feature_order
        ],
    }


def _group_name_from_toggle(group_id: str) -> str:
    bot_root = _require_bot_root()
    toggle_path = bot_root / "data" / "toggle" / f"{group_id}.json"
    normalized = _normalize_toggle_file(group_id, _read_json(toggle_path, {}))
    return normalized["group_name"] or group_id


def _first_string(entry: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None


@lru_cache(maxsize=4096)
def _read_image_dimensions(image_path: Path) -> tuple[int, int] | None:
    try:
        with Image.open(image_path) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError):
        return None

    if width <= 0 or height <= 0:
        return None
    return width, height


def list_quotes(group_id: str) -> list[dict[str, Any]]:
    bot_root = _require_bot_root()
    group_dir = bot_root / "data" / "quotes" / group_id
    members_raw = _read_json(group_dir / "members.json", [])
    index_raw = _read_json(group_dir / "index.json", {})

    ordered_members: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}

    if isinstance(members_raw, list):
        for member in members_raw:
            if isinstance(member, str) and member not in grouped:
                ordered_members.append(member)
                grouped[member] = []

    if isinstance(index_raw, dict):
        for quote_id, entry in index_raw.items():
            if not isinstance(quote_id, str) or not isinstance(entry, dict):
                continue
            member = entry.get("member")
            if not isinstance(member, str) or not member:
                continue
            filename = entry.get("filename") if isinstance(entry.get("filename"), str) else f"{quote_id}.png"
            image_path = group_dir / "images" / member / filename
            if not image_path.exists():
                continue
            if member not in grouped:
                ordered_members.append(member)
                grouped[member] = []
            image_dimensions = _read_image_dimensions(image_path)
            grouped[member].append(
                {
                    "id": quote_id,
                    "image_width": image_dimensions[0] if image_dimensions else None,
                    "image_height": image_dimensions[1] if image_dimensions else None,
                    "content": _first_string(entry, ["content", "text", "message", "quote"]),
                    "speaker_name": _first_string(
                        entry,
                        ["speaker_name", "speaker", "nickname", "display_name", "name", "sender_name", "author"],
                    ),
                    "avatar_url": _first_string(entry, ["avatar_url", "avatar", "avatarUrl"]),
                }
            )

    return [
        {"member": member, "entries": grouped[member]}
        for member in ordered_members
        if grouped.get(member)
    ]


def resolve_quote_image(group_id: str, quote_id: str) -> Path:
    bot_root = _require_bot_root()
    group_dir = bot_root / "data" / "quotes" / group_id
    index_raw = _read_json(group_dir / "index.json", {})
    entry = index_raw.get(quote_id) if isinstance(index_raw, dict) else None
    if not isinstance(entry, dict):
        raise FileNotFoundError(f"未找到语录 ID: {quote_id}")
    member = entry.get("member")
    if not isinstance(member, str) or not member:
        raise FileNotFoundError(f"语录缺少 member: {quote_id}")
    filename = entry.get("filename") if isinstance(entry.get("filename"), str) else f"{quote_id}.png"
    image_path = group_dir / "images" / member / filename
    if not image_path.exists():
        raise FileNotFoundError(f"语录图片不存在: {quote_id}")
    return image_path


def list_foods(group_id: str) -> list[dict[str, Any]]:
    bot_root = _require_bot_root()
    group_dir = bot_root / "data" / "food" / group_id
    index_raw = _read_json(group_dir / "index.json", {})
    foods: list[dict[str, Any]] = []
    if not isinstance(index_raw, dict):
        return foods

    for food_id, entry in index_raw.items():
        if not isinstance(food_id, str) or not isinstance(entry, dict):
            continue
        if entry.get("hidden"):
            continue
        filename = entry.get("filename") if isinstance(entry.get("filename"), str) else f"{food_id}.png"
        image_path = group_dir / "images" / filename
        if not image_path.exists():
            continue
        tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
        image_dimensions = _read_image_dimensions(image_path)
        foods.append(
            {
                "id": food_id,
                "name": entry.get("name")
                if isinstance(entry.get("name"), str) and entry.get("name")
                else food_id,
                "tags": [tag for tag in tags if isinstance(tag, str) and tag],
                "image_width": image_dimensions[0] if image_dimensions else None,
                "image_height": image_dimensions[1] if image_dimensions else None,
            }
        )
    return foods


def resolve_food_image(group_id: str, food_id: str) -> Path:
    bot_root = _require_bot_root()
    group_dir = bot_root / "data" / "food" / group_id
    index_raw = _read_json(group_dir / "index.json", {})
    entry = index_raw.get(food_id) if isinstance(index_raw, dict) else None
    if not isinstance(entry, dict):
        raise FileNotFoundError(f"未找到食物 ID: {food_id}")
    filename = entry.get("filename") if isinstance(entry.get("filename"), str) else f"{food_id}.png"
    image_path = group_dir / "images" / filename
    if not image_path.exists():
        raise FileNotFoundError(f"食物图片不存在: {food_id}")
    return image_path


def group_summary(group_id: str) -> dict[str, Any]:
    quotes = list_quotes(group_id)
    foods = list_foods(group_id)
    return {
        "group_id": group_id,
        "group_name": _group_name_from_toggle(group_id),
        "quote_member_count": len(quotes),
        "quote_count": sum(len(group["entries"]) for group in quotes),
        "food_count": len(foods),
    }
