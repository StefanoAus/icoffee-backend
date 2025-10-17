from __future__ import annotations
from typing import Any, Dict, List

from fastapi import APIRouter
from psycopg.rows import dict_row

from ..common import success, error_response
from ..db import get_connection
from ..utils import normalize_menu_structure, resolve_category_key

router = APIRouter()

@router.get("/menu", response_model=None)
def get_menu():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT mi.id, mi.category, mi.name, mo.name AS option_name
                FROM menu_items mi
                LEFT JOIN menu_options mo ON mo.item_id = mi.id
                ORDER BY mi.category, mi.name, mo.name
                """
            )
            rows = cursor.fetchall()

    grouped: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        item_id = row["id"]
        entry = grouped.setdefault(
            item_id,
            {"category": row["category"], "name": row["name"], "options": []},
        )
        option_name = row.get("option_name")
        if option_name and option_name not in entry["options"]:
            entry["options"].append(option_name)

    raw_menu = {"drinks": [], "foods": []}
    for entry in grouped.values():
        raw_menu.setdefault(entry["category"], []).append(
            {"name": entry["name"], "options": entry["options"]}
        )

    normalized = normalize_menu_structure(raw_menu)
    drinks = sorted(normalized["drinks"], key=lambda item: item["name"])
    foods = sorted(normalized["foods"], key=lambda item: item["name"])

    return success(drinks=drinks, foods=foods)

@router.post("/menu", response_model=None)
def add_menu_item(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    category_key = resolve_category_key(payload.get("category"))
    name = str(payload.get("name", "")).strip()
    options_payload = payload.get("options", [])
    options: List[str] = []
    if isinstance(options_payload, list):
        for option in options_payload:
            if isinstance(option, str):
                trimmed = option.strip()
                if trimmed and trimmed not in options:
                    options.append(trimmed)

    if category_key is None:
        return error_response(400, "Categoria non valida")
    if not name:
        return error_response(400, "Il nome della voce è obbligatorio")
    if not options:
        return error_response(400, "Specificare almeno una variante")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT 1 FROM menu_items WHERE category = %s AND name = %s",
                (category_key, name),
            )
            if cursor.fetchone() is not None:
                return error_response(409, "Esiste già una voce con questo nome")

            cursor.execute(
                """
                INSERT INTO menu_items (category, name)
                VALUES (%s, %s)
                RETURNING id
                """,
                (category_key, name),
            )
            item_id = cursor.fetchone()["id"] # type: ignore

            for option in options:
                cursor.execute(
                    "INSERT INTO menu_options (item_id, name) VALUES (%s, %s)",
                    (item_id, option),
                )

            conn.commit()

    return success()

@router.put("/menu", response_model=None)
def update_menu_item(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    category_key = resolve_category_key(payload.get("category"))
    name = str(payload.get("name", "")).strip()
    updates = payload.get("updates", {})

    if category_key is None or not name:
        return error_response(400, "Dati non validi per l'aggiornamento")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT id, name FROM menu_items WHERE category = %s AND name = %s",
                (category_key, name),
            )
            existing = cursor.fetchone()
            if existing is None:
                return error_response(404, "Voce non trovata")

            new_name = str(updates.get("newName", existing["name"])).strip()
            if not new_name:
                return error_response(400, "Il nome aggiornato non può essere vuoto")

            if new_name != existing["name"]:
                cursor.execute(
                    "SELECT 1 FROM menu_items WHERE category = %s AND name = %s",
                    (category_key, new_name),
                )
                if cursor.fetchone() is not None:
                    return error_response(409, "Esiste già una voce con il nuovo nome")

            options = None
            if "options" in updates:
                incoming = updates.get("options")
                if not isinstance(incoming, list):
                    return error_response(400, "Formato varianti non valido")
                parsed: List[str] = []
                for option in incoming:
                    if isinstance(option, str):
                        trimmed = option.strip()
                        if trimmed and trimmed not in parsed:
                            parsed.append(trimmed)
                if not parsed:
                    return error_response(400, "Inserire almeno una variante")
                options = parsed

            if new_name != existing["name"]:
                cursor.execute(
                    "UPDATE menu_items SET name = %s WHERE id = %s",
                    (new_name, existing["id"]),
                )

            if options is not None:
                cursor.execute("DELETE FROM menu_options WHERE item_id = %s", (existing["id"],))
                for option in options:
                    cursor.execute(
                        "INSERT INTO menu_options (item_id, name) VALUES (%s, %s)",
                        (existing["id"], option),
                    )

            conn.commit()

    return success()

@router.delete("/menu", response_model=None)
def delete_menu_item(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    category_key = resolve_category_key(payload.get("category"))
    name = str(payload.get("name", "")).strip()

    if category_key is None or not name:
        return error_response(400, "Dati non validi per l'eliminazione")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT id FROM menu_items WHERE category = %s AND name = %s",
                (category_key, name),
            )
            existing = cursor.fetchone()
            if existing is None:
                return error_response(404, "Voce non trovata")

            cursor.execute("DELETE FROM menu_items WHERE id = %s", (existing["id"],))
            conn.commit()

    return success()