from __future__ import annotations
from typing import Any, Dict, List

from fastapi import APIRouter, Query
from psycopg.rows import dict_row

from ..common import success, error_response
from ..db import get_connection

router = APIRouter()

@router.post("/login", response_model=None)
def login(payload: Dict[str, Any]):
    username = str(payload.get("username", ""))
    password = str(payload.get("password", ""))

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT username, password, group_name, role FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()

    if row and row["password"] == password:
        return success(
            username=row["username"],
            group=row["group_name"],
            role=row.get("role", "user"),
        )
    return error_response(401, "Credenziali non valide")


@router.get("/users", response_model=None)
def list_users(role: str = Query("user")):
    if role != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT username, password, group_name, role FROM users ORDER BY username"
            )
            rows = cursor.fetchall()

    users = [
        {
            "username": row["username"],
            "password": row["password"],
            "group": row["group_name"],
            "role": row.get("role", "user"),
        }
        for row in rows
    ]
    return success(users=users)


@router.post("/users", response_model=None)
def create_user(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    new_user = payload.get("user", {})
    username = str(new_user.get("username", "")).strip()
    password = new_user.get("password", "")
    group = str(new_user.get("group", "")).strip()
    role = "admin" if new_user.get("role") == "admin" else "user"

    if not username or not password or not group:
        return error_response(400, "Campi obbligatori mancanti")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT 1 FROM groups WHERE name = %s", (group,))
            if cursor.fetchone() is None:
                return error_response(400, "Seleziona un gruppo valido")

            cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cursor.fetchone() is not None:
                return error_response(409, "Username già esistente")

            cursor.execute(
                """
                INSERT INTO users (username, password, group_name, role)
                VALUES (%s, %s, %s, %s)
                """,
                (username, password, group, role),
            )
            conn.commit()

    return success()


@router.put("/users", response_model=None)
def update_user(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    username = str(payload.get("username", "")).strip()
    updates = payload.get("updates", {})

    if not username:
        return error_response(400, "Username mancante")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT username, group_name, role FROM users WHERE username = %s",
                (username,),
            )
            existing = cursor.fetchone()
            if existing is None:
                return error_response(404, "Utente non trovato")

            fields = []
            values: List[Any] = []

            if "password" in updates and updates["password"]:
                fields.append("password = %s")
                values.append(str(updates["password"]))

            if "group" in updates and str(updates["group"]).strip():
                new_group = str(updates["group"]).strip()
                cursor.execute("SELECT 1 FROM groups WHERE name = %s", (new_group,))
                if cursor.fetchone() is None:
                    return error_response(400, "Seleziona un gruppo valido")
                fields.append("group_name = %s")
                values.append(new_group)

            if "role" in updates:
                new_role = "admin" if updates.get("role") == "admin" else "user"
                if existing.get("role", "user") == "admin" and new_role != "admin":
                    cursor.execute(
                        "SELECT COUNT(*) AS total FROM users WHERE role = 'admin'"
                    )
                    admin_count_row = cursor.fetchone()
                    if admin_count_row and admin_count_row["total"] < 2:
                        return error_response(400, "Deve esistere almeno un amministratore")
                fields.append("role = %s")
                values.append(new_role)

            if not fields:
                return success()

            values.append(username)
            query = f"UPDATE users SET {', '.join(fields)} WHERE username = %s"
            cursor.execute(query, tuple(values))
            conn.commit()

    return success()


@router.delete("/users", response_model=None)
def delete_user(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    username = str(payload.get("username", "")).strip()
    if not username:
        return error_response(400, "Username mancante")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT username, role FROM users WHERE username = %s",
                (username,),
            )
            existing = cursor.fetchone()
            if existing is None:
                return error_response(404, "Utente non trovato")

            if existing.get("role", "user") == "admin":
                cursor.execute(
                    "SELECT COUNT(*) AS total FROM users WHERE role = 'admin'"
                )
                admin_count_row = cursor.fetchone()
                if admin_count_row and admin_count_row["total"] < 2:
                    return error_response(400, "Non è possibile eliminare l'unico admin")

            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            if cursor.rowcount == 0:
                return error_response(500, "Impossibile eliminare l'utente")
            conn.commit()

    return success()