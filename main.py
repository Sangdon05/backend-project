from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402

from feature.auth.presentation.routers.v1.router import router as auth_router  # noqa: E402
from feature.user.presentation.routers.v1.router import router as user_router  # noqa: E402
from shared.core.database import close_db  # noqa: E402
from shared.core.exception_handlers import register_exception_handlers  # noqa: E402
from wiring.auth import wire_auth  # noqa: E402
from wiring.user import wire_user  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(title="Backend Project API", lifespan=lifespan)

    register_exception_handlers(app)

    wire_user(app)
    wire_auth(app)

    app.include_router(auth_router)
    app.include_router(user_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
