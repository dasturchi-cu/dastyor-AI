"""Admin panel routers."""
from aiogram import Router

from features.admin import handlers

router = Router()
router.include_router(handlers.router)
