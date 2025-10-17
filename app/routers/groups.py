from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, Query
from ..storage import GROUPS_FILE, USERS_FILE, read_json_file, write_json_file
from ..common import success, error_response

router = APIRouter()

@router.get("/groups", response_model=None)
def list_groups(role: str = Query("user")):
    if role != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")
    groups = read_json_file(GROUPS_FILE) or []
    return success(groups=list(map(str, groups)))

@router.post("/groups", response_model=None)
def create_group(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    name = str(payload.get("name", "")).strip()
    if not name:
        return error_response(400, "Il nome del gruppo è obbligatorio")

    groups = read_json_file(GROUPS_FILE) or []
    if name in groups:
        return error_response(409, "Esiste già un gruppo con questo nome")

    groups.append(name)
    if not write_json_file(GROUPS_FILE, groups):
        return error_response(500, "Impossibile salvare i gruppi")

    return success()

@router.put("/groups", response_model=None)
def rename_group(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    old_name = str(payload.get("oldName", "")).strip()
    new_name = str(payload.get("newName", "")).strip()

    if not old_name or not new_name:
        return error_response(400, "Specificare i nomi del gruppo da modificare")

    groups = read_json_file(GROUPS_FILE) or []
    if old_name not in groups:
        return error_response(404, "Gruppo non trovato")
    if old_name == new_name:
        return success()
    if new_name in groups:
        return error_response(409, "Esiste già un gruppo con il nuovo nome")

    users = read_json_file(USERS_FILE) or []
    for user in users:
        if user.get("group") == old_name:
            user["group"] = new_name

    if not write_json_file(USERS_FILE, users):
        return error_response(500, "Impossibile aggiornare gli utenti")

    updated_groups = [new_name if group == old_name else group for group in groups]
    normalized_groups = []
    for group in updated_groups:
        if isinstance(group, str):
            trimmed = group.strip()
            if trimmed and trimmed not in normalized_groups:
                normalized_groups.append(trimmed)

    if not write_json_file(GROUPS_FILE, normalized_groups):
        return error_response(500, "Impossibile salvare i gruppi")

    return success()

@router.delete("/groups", response_model=None)
def delete_group(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    name = str(payload.get("name", "")).strip()
    if not name:
        return error_response(400, "Specificare il gruppo da eliminare")

    groups = read_json_file(GROUPS_FILE) or []
    if name not in groups:
        return error_response(404, "Gruppo non trovato")

    users = read_json_file(USERS_FILE) or []
    for user in users:
        if user.get("group") == name:
            return error_response(400, "Impossibile eliminare un gruppo assegnato a degli utenti")

    groups = [group for group in groups if group != name]
    if not write_json_file(GROUPS_FILE, groups):
        return error_response(500, "Impossibile salvare i gruppi")

    return success()
