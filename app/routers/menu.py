from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter
from ..storage import MENU_FILE, read_json_file, write_json_file
from ..common import success, error_response
from ..utils import normalize_menu_structure, resolve_category_key, get_item_index

router = APIRouter()

@router.get("/menu", response_model=None)
def get_menu():
    menu = normalize_menu_structure(read_json_file(MENU_FILE))
    return success(drinks=menu["drinks"], foods=menu["foods"])

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

    menu = normalize_menu_structure(read_json_file(MENU_FILE))
    if get_item_index(menu, category_key, name) != -1:
        return error_response(409, "Esiste già una voce con questo nome")

    menu[category_key].append({ "name": name, "options": options })
    if not write_json_file(MENU_FILE, menu):
        return error_response(500, "Impossibile salvare il menu")

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

    menu = normalize_menu_structure(read_json_file(MENU_FILE))
    index = get_item_index(menu, category_key, name)
    if index == -1:
        return error_response(404, "Voce non trovata")

    current = menu[category_key][index]
    new_name = str(updates.get("newName", current["name"])).strip()
    if not new_name:
        return error_response(400, "Il nome aggiornato non può essere vuoto")

    if new_name != current["name"] and get_item_index(menu, category_key, new_name) != -1:
        return error_response(409, "Esiste già una voce con il nuovo nome")

    options = current["options"]
    if "options" in updates:
        incoming = updates.get("options")
        if not isinstance(incoming, list):
            return error_response(400, "Formato varianti non valido")
        options = []
        for option in incoming:
            if isinstance(option, str):
                trimmed = option.strip()
                if trimmed and trimmed not in options:
                    options.append(trimmed)
        if not options:
            return error_response(400, "Inserire almeno una variante")

    menu[category_key][index] = {"name": new_name, "options": options}
    if not write_json_file(MENU_FILE, menu):
        return error_response(500, "Impossibile salvare il menu")

    return success()

@router.delete("/menu", response_model=None)
def delete_menu_item(payload: Dict[str, Any]):
    if payload.get("actorRole", "user") != "admin":
        return error_response(403, "Operazione permessa solo agli amministratori")

    category_key = resolve_category_key(payload.get("category"))
    name = str(payload.get("name", "")).strip()

    if category_key is None or not name:
        return error_response(400, "Dati non validi per l'eliminazione")

    menu = normalize_menu_structure(read_json_file(MENU_FILE))
    index = get_item_index(menu, category_key, name)
    if index == -1:
        return error_response(404, "Voce non trovata")

    menu[category_key].pop(index)
    if not write_json_file(MENU_FILE, menu):
        return error_response(500, "Impossibile salvare il menu")

    return success()
