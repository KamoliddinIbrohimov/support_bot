from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot import bot_context
from bot.handlers import get_all_routers
from bot.state_manager import StateManager
from config.logger import logger, setup_logging
from config.settings import settings


async def on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    bot_context.bot_id = me.id
    bot_context.bot_username = me.username or ""

    from bot import group_cache, conversation_tracker
    from bot import resolution_handler
    await group_cache.load()
    resolution_handler.set_bot(bot)
    conversation_tracker.set_callback(resolution_handler.on_resolved)

    logger.info(f"Bot ishga tushdi: @{me.username} (id={me.id})")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Bot to'xtatilmoqda...")
    await bot.session.close()


async def main() -> None:
    setup_logging()
    logger.info("Support Bot starting...")

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    storage = RedisStorage(redis=redis)
    state_manager = StateManager(redis)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Inject state_manager so handlers can receive it via DI
    dp["state_manager"] = state_manager

    for router in get_all_routers():
        dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")
