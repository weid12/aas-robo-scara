# ------------------------------------------------------------------------------------------------------------------
#   API de gerenciamento de usuários (FastAPI).
#   Define os endpoints para registro e consulta de usuários.
# ------------------------------------------------------------------------------------------------------------------

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import engine, get_db

# Cria tabelas
models.Base.metadata.create_all(bind=engine)

# Cria aplicação FastAPI
api = FastAPI(title="User Management API", version="1.0.0")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/health")
def healthcheck() -> dict:
    """Healthcheck endpoint."""
    return {"status": "ok"}


@api.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registra novo usuário no sistema.
    """
    try:
        user = crud.create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@api.get("/users", response_model=schemas.UserList)
def list_all_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos os usuários registrados.
    """
    users = crud.list_users(db, skip=skip, limit=limit)
    total = crud.count_users(db)
    return {"users": users, "total": total}


@api.get("/users/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Busca usuário específico por ID.
    """
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return user


@api.put("/users/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, user_data: schemas.UserUpdate, db: Session = Depends(get_db)):
    """
    Atualiza dados de um usuário existente.
    """
    try:
        user = crud.update_user(db, user_id, user_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
