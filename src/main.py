from fastapi import FastAPI

from src.routes import movies as movie_routes


app = FastAPI(
    title="Movies homework",
    description="Description of project"
)

api_version_prefix = "/api/v1"

app.include_router(movie_routes.router, prefix=f"{api_version_prefix}/theater", tags=["theater"])
