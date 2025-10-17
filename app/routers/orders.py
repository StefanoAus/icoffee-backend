from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row

from ..common import success, error_response
from ..db import get_connection
from ..utils import extract_choice, normalize_order_payload

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

    if has_drink and not _choice_exists("drinks", drink_item, drink_variant):
        return error_response(400, "La voce selezionata non è più disponibile")
    if has_food and not _choice_exists("foods", food_item, food_variant):
        return error_response(400, "La voce selezionata non è più disponibile")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO orders (
                    order_date, username, group_name,
                    drink_item, drink_variant,
                    food_item, food_variant
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_date, username) DO UPDATE SET
                    group_name = EXCLUDED.group_name,
                    drink_item = EXCLUDED.drink_item,
                    drink_variant = EXCLUDED.drink_variant,
                    food_item = EXCLUDED.food_item,
                    food_variant = EXCLUDED.food_variant
                """,
                (
                    current_date,
                    username,
                    group,
                    drink_item if has_drink else None,
                    drink_variant if has_drink else None,
                    food_item if has_food else None,
                    food_variant if has_food else None,
                ),
            )
            conn.commit()

    return success()

@router.get("/orders", response_model=None)
def get_orders(
    date_param: Optional[str] = Query(default=None, alias="date"),
    group: Optional[str] = None,
    role: str = "user",
):
    requested_date = date_param or date.today().isoformat()
    requested_group = (group or "").strip()

    if role != "admin" and not requested_group:
        return error_response(400, "Gruppo richiesto mancante")

    params: List[Any] = [requested_date]
    filters = ""
    if role != "admin":
        filters = " AND group_name = %s"
        params.append(requested_group)
    elif requested_group:
        filters = " AND group_name = %s"
        params.append(requested_group)

    query = (
        """
        SELECT username, group_name, drink_item, drink_variant, food_item, food_variant
        FROM orders
        WHERE order_date = %s
        """
        + filters
        + " ORDER BY group_name, username"
    )

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

    normalized: List[Dict[str, Any]] = []
    for row in rows:
        order_payload: Dict[str, Any] = {}
        if row.get("drink_item") and row.get("drink_variant"):
            order_payload["drink"] = {
                "item": row["drink_item"],
                "variant": row["drink_variant"],
            }
        if row.get("food_item") and row.get("food_variant"):
            order_payload["food"] = {
                "item": row["food_item"],
                "variant": row["food_variant"],
            }

        normalized.append(
            {
                "username": row["username"],
                "group": row["group_name"],
                "order": normalize_order_payload(order_payload),
            }
        )

    return JSONResponse(content=normalized)


def _choice_exists(category: str, item_name: str, variant: str) -> bool:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM menu_items mi
                JOIN menu_options mo ON mo.item_id = mi.id
                WHERE mi.category = %s AND mi.name = %s AND mo.name = %s
                LIMIT 1
                """,
                (category, item_name, variant),
            )
            return cursor.fetchone() is not None