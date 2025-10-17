from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, Query
from ..storage import USERS_FILE, GROUPS_FILE, read_json_file, write_json_file
from ..common import success, error_response
from ..utils import count_admins

router = APIRouter()

@router.post("/login", response_model=None)
def login(payload: Dict[str, Any]):
    username = str(payload.get("username", ""))
    password = str(payload.get("password", ""))

    users = read_json_file(USERS_FILE) or []
    for user in users:
        if user.get("username") == username and user.get("password") == password:
            return success(
                username=user.get("username"),
                group=user.get("group"),
                role=user.get("role", "user"),
            )
    return error_response(401, "Credenziali non valide")


@router.get("/users", response_model=None)
def list_users(role: str = Query("user")):
    if role != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")
    users = read_json_file(USERS_FILE) or []
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

    users = read_json_file(USERS_FILE) or []
    groups = read_json_file(GROUPS_FILE) or []

    if group not in groups:
        return error_response(400, "Seleziona un gruppo valido")

    for user in users:
        if user.get("username") == username:
            return error_response(409, "Username già esistente")

    users.append({
        "username": username,
        "password": password,
        "group": group,
        "role": role,
    })

    if not write_json_file(USERS_FILE, users):
        return error_response(500, "Impossibile salvare gli utenti")

    return success()


@router.put("/users", response_model=None)
def update_user(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    username = str(payload.get("username", "")).strip()
    updates = payload.get("updates", {})

    if not username:
        return error_response(400, "Username mancante")

    users = read_json_file(USERS_FILE) or []
    groups = read_json_file(GROUPS_FILE) or []

    found = False
    for user in users:
        if user.get("username") == username:
            found = True
            if "password" in updates and updates["password"]:
                user["password"] = updates["password"]
            if "group" in updates and str(updates["group"]).strip():
                new_group = str(updates["group"]).strip()
                if new_group not in groups:
                    return error_response(400, "Seleziona un gruppo valido")
                user["group"] = new_group
            if "role" in updates:
                new_role = "admin" if updates.get("role") == "admin" else "user"
                if user.get("role", "user") == "admin" and new_role != "admin":
                    if count_admins(users) < 2:
                        return error_response(400, "Deve esistere almeno un amministratore")
                user["role"] = new_role
            break

    if not found:
        return error_response(404, "Utente non trovato")

    if not write_json_file(USERS_FILE, users):
        return error_response(500, "Impossibile salvare gli utenti")

    return success()


@router.delete("/users", response_model=None)
def delete_user(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    username = str(payload.get("username", "")).strip()
    if not username:
        return error_response(400, "Username mancante")

    users = read_json_file(USERS_FILE) or []

    index = next((i for i, user in enumerate(users) if user.get("username") == username), -1)
    if index == -1:
        return error_response(404, "Utente non trovato")

    if users[index].get("role", "user") == "admin":
        admins = count_admins(users)
        if admins < 2:
            return error_response(400, "Non è possibile eliminare l'unico admin")

    users.pop(index)

    if not write_json_file(USERS_FILE, users):
        return error_response(500, "Impossibile salvare gli utenti")

    return success()
