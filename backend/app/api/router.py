from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.board import router as board_router
from app.api.communications import router as communications_router
from app.api.contracts import router as contracts_router
from app.api.customers import router as customers_router
from app.api.dashboard import router as dashboard_router
from app.api.dicts import router as dicts_router
from app.api.documents import router as documents_router
from app.api.follow_ups import router as follow_ups_router
from app.api.notifications import router as notifications_router
from app.api.payments import router as payments_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router
from app.api.audit_logs import router as audit_logs_router
from app.api.search import router as search_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(customers_router)
api_router.include_router(contracts_router)
api_router.include_router(tasks_router)
api_router.include_router(documents_router)
api_router.include_router(communications_router)
api_router.include_router(payments_router)
api_router.include_router(board_router)
api_router.include_router(dashboard_router)
api_router.include_router(notifications_router)
api_router.include_router(follow_ups_router)
api_router.include_router(audit_logs_router)
api_router.include_router(dicts_router)
api_router.include_router(search_router)
