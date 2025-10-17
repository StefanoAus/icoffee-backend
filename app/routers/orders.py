from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date
from fastapi import APIRouter, Query
from ..storage import ORDERS_FILE, MENU_FILE, read_json_file, write_json_file
from ..common import success, error_response
from ..utils import normalize_menu_structure, extract_choice, choice_exists, normalize_order_payload
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/orders", response_model=None)
def save_order(payload: Dict[str, Any]):
    username = str(payload.get("username", "")).strip()
    group = str(payload.get("group", "")).strip()
    order_payload = payload.get("order")
    current_date = date.today().isoformat()

    drink_item, drink_variant = extract_choice(order_payload, "drink")
    food_item, food_variant = extract_choice(order_payload, "food")

    if not username or not group:
        return error_response(400, "Dati mancanti o non validi per l'ordine")

    has_drink = bool(drink_item and drink_variant)
    has_food = bool(food_item and food_variant)

    if not has_drink and not has_food:
        return error_response(400, "Seleziona almeno una bevanda o un cibo")

    menu = normalize_menu_structure(read_json_file(MENU_FILE))
    if has_drink and not choice_exists(menu["drinks"], drink_item, drink_variant):
        return error_response(400, "La voce selezionata non è più disponibile")
    if has_food and not choice_exists(menu["foods"], food_item, food_variant):
        return error_response(400, "La voce selezionata non è più disponibile")

    orders = read_json_file(ORDERS_FILE) or {}
    if not isinstance(orders, dict):
        orders = {}

    order_data: Dict[str, Any] = {}
    if has_drink:
        order_data["drink"] = {"item": drink_item, "variant": drink_variant}
    if has_food:
        order_data["food"] = {"item": food_item, "variant": food_variant}

    day_orders = list(orders.get(current_date, []))
    updated = False
    for entry in day_orders:
        if entry.get("username") == username:
            entry["order"] = order_data
            entry["group"] = group
            updated = True
            break
    if not updated:
        day_orders.append({"username": username, "group": group, "order": order_data})

    orders[current_date] = day_orders

    if not write_json_file(ORDERS_FILE, orders):
        return error_response(500, "Impossibile salvare l'ordine")

    return success()

@router.get("/orders", response_model=None)
def get_orders(
    date_param: Optional[str] = Query(default=None, alias="date"),
    group: Optional[str] = None,
    role: str = "user",
):
    requested_date = date_param or date.today().isoformat()
    orders = read_json_file(ORDERS_FILE) or {}
    if not isinstance(orders, dict):
        orders = {}

    entries = list(orders.get(requested_date, []))
    requested_group = (group or "").strip()

    if role != "admin":
        if not requested_group:
            return error_response(400, "Gruppo richiesto mancante")
        entries = [entry for entry in entries if entry.get("group") == requested_group]
    elif requested_group:
        entries = [entry for entry in entries if entry.get("group") == requested_group]

    entries.sort(key=lambda entry: (entry.get("group", ""), entry.get("username", "")))

    normalized = []
    for entry in entries:
        normalized.append({
            "username": entry.get("username"),
            "group": entry.get("group"),
            "order": normalize_order_payload(entry.get("order")),
        })

    return JSONResponse(content=normalized)
