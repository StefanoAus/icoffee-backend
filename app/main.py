from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .common import success
from .routers.users import router as users_router
from .routers.groups import router as groups_router
from .routers.menu import router as menu_router
from .routers.orders import router as orders_router
from .routers.payments import router as payments_router

app = FastAPI(title="Colazione Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers without prefix to keep same paths
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(menu_router)
app.include_router(orders_router)
app.include_router(payments_router)

@app.get("/", response_model=None)
def healthcheck():
    return success(message="Colazione backend attivo")
