from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date
from fastapi import APIRouter, Query
from ..storage import USERS_FILE, PAYMENTS_FILE, read_json_file, write_json_file
from ..common import success, error_response
from ..utils import ensure_group_access

router = APIRouter()

@router.get("/payments", response_model=None)
def get_payments(
    group: str = Query(""),
    role: str = Query("user"),
    username: str = Query(""),
    date_param: Optional[str] = Query(default=None, alias="date"),
):
    group = group.strip()
    username = username.strip()
    requested_date = date_param.strip() if isinstance(date_param, str) and date_param else date.today().isoformat()

    if not group:
        return error_response(400, "Gruppo richiesto mancante")

    users = read_json_file(USERS_FILE) or []
    payments = read_json_file(PAYMENTS_FILE) or {}
    if not isinstance(payments, dict):
        payments = {}

    if role != "admin":
        if not username:
            return error_response(400, "Utente richiesto mancante")
        if not ensure_group_access(users, group, username):
            return error_response(403, "Accesso non consentito al gruppo richiesto")

    group_members = [user.get("username") for user in users if user.get("group") == group]

    counts = {member: 0 for member in group_members}
    log: List[Dict[str, Any]] = []

    for payment_date, per_group in payments.items():
        if isinstance(per_group, dict):
            payer = str(per_group.get(group, "")).strip()
            if payer:
                counts[payer] = counts.get(payer, 0) + 1
                log.append({"date": payment_date, "username": payer})

    log.sort(key=lambda entry: entry["date"], reverse=True)

    history = [
        {"username": member, "count": counts.get(member, 0)}
        for member in sorted(counts.keys())
    ]
    history.sort(key=lambda entry: (-entry["count"], entry["username"]))

    payer_for_date = None
    day_record = payments.get(requested_date)
    if isinstance(day_record, dict):
        recorded = str(day_record.get(group, "")).strip()
        if recorded:
            payer_for_date = {"username": recorded, "date": requested_date}

    return success(group=group, date=requested_date, payer=payer_for_date, totals=history, log=log)


@router.post("/payments", response_model=None)
def register_payment(payload: Dict[str, Any]):
    group = str(payload.get("group", "")).strip()
    payer = str(payload.get("payer", "")).strip()
    role = payload.get("role", "user")
    actor = str(payload.get("actor", "")).strip()
    requested_date = str(payload.get("date", "")).strip() or date.today().isoformat()

    if not group or not payer:
        return error_response(400, "Dati mancanti o non validi per il pagamento")

    users = read_json_file(USERS_FILE) or []
    payer_user = next((user for user in users if user.get("username") == payer), None)
    if not payer_user:
        return error_response(404, "Utente non trovato")
    if payer_user.get("group") != group:
        return error_response(400, "L'utente selezionato non appartiene al gruppo")

    if role != "admin":
        actor = actor or payer
        if not ensure_group_access(users, group, actor):
            return error_response(403, "Accesso non consentito al gruppo richiesto")
        if actor != payer:
            return error_response(403, "Non puoi registrare il pagamento per un altro utente")

    payments = read_json_file(PAYMENTS_FILE) or {}
    if not isinstance(payments, dict):
        payments = {}

    day_record = payments.get(requested_date)
    if not isinstance(day_record, dict):
        day_record = {}
    day_record[group] = payer
    payments[requested_date] = day_record

    if not write_json_file(PAYMENTS_FILE, payments):
        return error_response(500, "Impossibile salvare il pagamento")

    return success()
