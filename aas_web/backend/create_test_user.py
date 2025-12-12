# Script para criar usuário de teste
import sys
sys.path.insert(0, '.')

from user_management.database import SessionLocal, engine, Base
from user_management import crud, schemas, models

# Cria tabelas
Base.metadata.create_all(bind=engine)

# Cria sessão
db = SessionLocal()

try:
    # Verifica se já existe
    existing = crud.get_user_by_username(db, "admin")
    if existing:
        print(f"✓ Usuário 'admin' já existe (ID: {existing.id})")
        print(f"  Role: {existing.role}")
        print(f"  Profile: {existing.profile_type}")
    else:
        # Cria usuário admin
        user_data = schemas.UserCreate(
            username="admin",
            email="admin@example.com",
            full_name="Administrador",
            password="admin123",
            role=models.UserRole.DIRECTOR,
            profile_type=models.ProfileType.ADMIN,
            department="IT"
        )
        
        user = crud.create_user(db, user_data)
        print(f"✓ Usuário 'admin' criado com sucesso!")
        print(f"  ID: {user.id}")
        print(f"  Role: {user.role}")
        print(f"  Profile: {user.profile_type}")
        
except Exception as e:
    print(f"✗ Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
