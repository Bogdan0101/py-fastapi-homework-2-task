import math
import operator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.database.session_postgresql import get_postgresql_db
from src.database.models import MovieModel
from src.database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from src.schemas.movies import (
    MovieListResponseSchema,
    MovieDetail,
    MovieCreate,
    MovieUpdate,
)

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_postgresql_db),
):
    total_items = await db.scalar(select(func.count()).select_from(MovieModel))
    total_items = total_items or 0
    if total_items == 0:
        return MovieListResponseSchema(
            movies=[],
            prev_page=None,
            next_page=None,
            total_pages=0,
            total_items=0,
        )

    total_pages = math.ceil(total_items / per_page)
    if page > total_pages and total_items > 0:
        raise HTTPException(status_code=404, detail="No movies found.")
    offset = (page - 1) * per_page
    if offset >= total_items:
        raise HTTPException(status_code=404, detail="No movies found.")
    result = await db.execute(
        select(MovieModel).order_by(desc(MovieModel.id)).offset(offset).limit(per_page)
    )
    movies = result.scalars().all()

    base_url = "/theater/movies/"
    prev_page = f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = (
        f"{base_url}?page={page + 1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.get("/movies/{movie_id}/", response_model=MovieDetail)
async def get_movie_by_id(movie_id: int, db: AsyncSession = Depends(get_postgresql_db)):
    query = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    result = await db.execute(query)
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )
    return movie


async def get_or_create(db, model, field, value):
    stmt = select(model).where(operator.eq(getattr(model, field), value))
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()
    if instance:
        return instance
    else:
        instance = model(**{field: value})
        db.add(instance)
        await db.flush()
        return instance


@router.post(
    "/movies/", response_model=MovieDetail, status_code=status.HTTP_201_CREATED
)
async def post_movies(
    movie: MovieCreate, db: AsyncSession = Depends(get_postgresql_db)
):
    movie_exist = await db.execute(
        select(MovieModel).where(
            MovieModel.name == movie.name, MovieModel.date == movie.date
        )
    )
    if movie_exist.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists.",
        )

    new_movie = MovieModel(
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
    )
    new_movie.country = await get_or_create(db, CountryModel, "code", movie.country)
    new_movie.genres = [
        await get_or_create(db, GenreModel, "name", g) for g in movie.genres
    ]
    new_movie.actors = [
        await get_or_create(db, ActorModel, "name", a) for a in movie.actors
    ]
    new_movie.languages = [
        await get_or_create(db, LanguageModel, "name", l) for l in movie.languages
    ]

    db.add(new_movie)
    try:
        await db.commit()
        return await get_movie_by_id(new_movie.id, db)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_postgresql_db)):
    query = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(query)
    movie = result.scalar_one_or_none()
    if movie is None:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )
    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def patch_movie(
    movie_id: int,
    movie_update: MovieUpdate,
    db: AsyncSession = Depends(get_postgresql_db),
):
    query = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(query)
    movie = result.scalar_one_or_none()
    if movie is None:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )
    update_data = movie_update.model_dump(exclude_unset=True)
    if not update_data:
        return {"detail": "Movie updated successfully."}

    for key, value in update_data.items():
        setattr(movie, key, value)
    try:
        await db.commit()
        return {"detail": "Movie updated successfully."}
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
