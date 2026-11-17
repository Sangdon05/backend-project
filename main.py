from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from feature.auth.presentation.routers.v1.router import (
    router as auth_router,
)
from feature.board.presentation.routers.v1.router import (
    router as board_router,
)
from feature.user.presentation.routers.v1.router import (
    router as user_router,
)
from shared.core import database
from shared.core.database import close_db
from shared.core.exception_handlers import register_exception_handlers
from shared.core.models import create_tables
from wiring.auth import wire_auth
from wiring.board import wire_board
from wiring.user import wire_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables(database.engine)
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(title="Backend Project API", lifespan=lifespan)

    register_exception_handlers(app)

    wire_user(app)
    wire_auth(app)
    wire_board(app)

    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(board_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
