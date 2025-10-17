from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

def normalize_menu_structure(menu: Any) -> Dict[str, List[Dict[str, Any]]]:
    if not isinstance(menu, dict):
        menu = {}
    drinks = menu.get("drinks") if isinstance(menu.get("drinks"), list) else []
    foods = menu.get("foods") if isinstance(menu.get("foods"), list) else []
    return {
        "drinks": [item for item in map(normalize_menu_item, drinks) if item["name"] and item["options"]], # type: ignore
        "foods": [item for item in map(normalize_menu_item, foods) if item["name"] and item["options"]], # type: ignore
    }

def normalize_menu_item(item: Any) -> Dict[str, Any]:
    name = ""
    options: List[str] = []
    if isinstance(item, dict):
        name = str(item.get("name", "")).strip()
        options_payload = item.get("options", [])
        if isinstance(options_payload, list):
            for option in options_payload:
                if isinstance(option, str):
                    trimmed = option.strip()
                    if trimmed and trimmed not in options:
                        options.append(trimmed)
    return {"name": name, "options": options}

def resolve_category_key(category: Any) -> Optional[str]:
    if not isinstance(category, str):
        return None
    normalized = category.strip().lower()
    if normalized in {"drinks", "drink"}:
        return "drinks"
    if normalized in {"foods", "food"}:
        return "foods"
    return None

def extract_choice(order_payload: Any, key: str) -> Tuple[str, str]:
    if isinstance(order_payload, dict):
        choice = order_payload.get(key)
        if isinstance(choice, dict):
            item = str(choice.get("item", "")).strip()
            variant = str(choice.get("variant", "")).strip()
            return item, variant
    return "", ""

def normalize_order_payload(order: Any) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    if isinstance(order, dict):
        drink = order.get("drink")
        if isinstance(drink, dict):
            item = str(drink.get("item", "")).strip()
            variant = str(drink.get("variant", "")).strip()
            if item and variant:
                normalized["drink"] = {"item": item, "variant": variant}
        food = order.get("food")
        if isinstance(food, dict):
            item = str(food.get("item", "")).strip()
            variant = str(food.get("variant", "")).strip()
            if item and variant:
                normalized["food"] = {"item": item, "variant": variant}
        if "legacyText" in order:
            legacy = str(order.get("legacyText", "")).strip()
            if legacy:
                normalized["legacyText"] = legacy
        if normalized:
            return normalized
    if isinstance(order, str):
        legacy = order.strip()
        if legacy:
            return {"legacyText": legacy}
    return normalized