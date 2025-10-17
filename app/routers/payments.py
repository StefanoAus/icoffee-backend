from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date

from fastapi import APIRouter, Query
from psycopg.rows import dict_row

from ..common import success, error_response
from ..db import get_connection

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

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT username FROM users WHERE group_name = %s ORDER BY username",
                (group,),
            )
            group_members = [row["username"] for row in cursor.fetchall()]

            if role != "admin":
                if not username:
                    return error_response(400, "Utente richiesto mancante")
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = %s AND group_name = %s",
                    (username, group),
                )
                if cursor.fetchone() is None:
                    return error_response(403, "Accesso non consentito al gruppo richiesto")

            counts = {member: 0 for member in group_members}

            cursor.execute(
                """
                SELECT payer_username, COUNT(*) AS total
                FROM payments
                WHERE group_name = %s
                GROUP BY payer_username
                """,
                (group,),
            )
            for row in cursor.fetchall():
                payer = row.get("payer_username")
                if payer:
                    counts[payer] = row.get("total", 0)

            cursor.execute(
                """
                SELECT payment_date, payer_username
                FROM payments
                WHERE group_name = %s
                ORDER BY payment_date DESC
                """,
                (group,),
            )
            log = [
                {"date": row["payment_date"].isoformat(), "username": row["payer_username"]}
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT payer_username FROM payments
                WHERE group_name = %s AND payment_date = %s
                """,
                (group, requested_date),
            )
            payer_row = cursor.fetchone()

    history = [
        {"username": member, "count": counts.get(member, 0)}
        for member in sorted(counts.keys())
    ]
    history.sort(key=lambda entry: (-entry["count"], entry["username"]))

    payer_for_date = None
    if payer_row and payer_row.get("payer_username"):
        payer_for_date = {"username": payer_row["payer_username"], "date": requested_date}

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

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT username, group_name FROM users WHERE username = %s",
                (payer,),
            )
            payer_row = cursor.fetchone()
            if payer_row is None:
                return error_response(404, "Utente non trovato")
            if payer_row.get("group_name") != group:
                return error_response(400, "L'utente selezionato non appartiene al gruppo")

            if role != "admin":
                actor = actor or payer
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = %s AND group_name = %s",
                    (actor, group),
                )
                if cursor.fetchone() is None:
                    return error_response(403, "Accesso non consentito al gruppo richiesto")
                if actor != payer:
                    return error_response(403, "Non puoi registrare il pagamento per un altro utente")

            cursor.execute(
                """
                INSERT INTO payments (payment_date, group_name, payer_username)
                VALUES (%s, %s, %s)
                ON CONFLICT (payment_date, group_name) DO UPDATE SET
                    payer_username = EXCLUDED.payer_username
                """,
                (requested_date, group, payer),
            )
            conn.commit()

    return success()