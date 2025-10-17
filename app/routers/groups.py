from __future__ import annotations
from typing import Any, Dict

from fastapi import APIRouter, Query
from psycopg.rows import dict_row

from ..common import success, error_response
from ..db import get_connection

router = APIRouter()

@router.get("/groups", response_model=None)
def list_groups(role: str = Query("user")):
    if role != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT name FROM groups ORDER BY name")
            rows = cursor.fetchall()

    groups = [str(row["name"]) for row in rows]
    return success(groups=groups)

@router.post("/groups", response_model=None)
def create_group(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    name = str(payload.get("name", "")).strip()
    if not name:
        return error_response(400, "Il nome del gruppo è obbligatorio")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT 1 FROM groups WHERE name = %s", (name,))
            if cursor.fetchone() is not None:
                return error_response(409, "Esiste già un gruppo con questo nome")

            cursor.execute("INSERT INTO groups (name) VALUES (%s)", (name,))
            conn.commit()

    return success()

@router.put("/groups", response_model=None)
def rename_group(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    old_name = str(payload.get("oldName", "")).strip()
    new_name = str(payload.get("newName", "")).strip()

    if not old_name or not new_name:
        return error_response(400, "Specificare i nomi del gruppo da modificare")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT 1 FROM groups WHERE name = %s", (old_name,))
            if cursor.fetchone() is None:
                return error_response(404, "Gruppo non trovato")

            if old_name == new_name:
                return success()

            cursor.execute("SELECT 1 FROM groups WHERE name = %s", (new_name,))
            if cursor.fetchone() is not None:
                return error_response(409, "Esiste già un gruppo con il nuovo nome")

            cursor.execute(
                "UPDATE groups SET name = %s WHERE name = %s",
                (new_name, old_name),
            )
            conn.commit()

    return success()

@router.delete("/groups", response_model=None)
def delete_group(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    name = str(payload.get("name", "")).strip()
    if not name:
        return error_response(400, "Specificare il gruppo da eliminare")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT 1 FROM groups WHERE name = %s", (name,))
            if cursor.fetchone() is None:
                return error_response(404, "Gruppo non trovato")

            cursor.execute(
                "SELECT COUNT(*) AS total FROM users WHERE group_name = %s",
                (name,),
            )
            row = cursor.fetchone()
            if row and row["total"] > 0:
                return error_response(
                    400, "Impossibile eliminare un gruppo assegnato a degli utenti"
                )

            cursor.execute("DELETE FROM groups WHERE name = %s", (name,))
            conn.commit()

    return success()