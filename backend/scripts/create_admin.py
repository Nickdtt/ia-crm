"""
Script para criar usuário admin no banco de forma segura.

Uso:
    python create_admin.py

Cria um usuário com:
- Email: mdf.nicolas@gmail.com
- Senha: 612662nf (hasheada com bcrypt)
- Role: admin
- is_active: true
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.authService import hash_password


async def create_admin():
    """Cria usuário admin no banco."""
    
    email = "mdf.nicolas@gmail.com"
    password = "612662nf"
    
    # 1. Hash da senha usando bcrypt (mesmo método do AuthService)
    hashed_password = hash_password(password)
    
    print(f"📝 Criando admin...")
    print(f"   Email: {email}")
    print(f"   is_active: true")
    
    # 2. Criar objeto User
    admin = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    # 3. Inserir no banco
    async with AsyncSessionLocal() as session:
        try:
            session.add(admin)
            await session.commit()
            
            print(f"\n✅ Admin criado com sucesso!")
            print(f"   ID: {admin.id}")
            print(f"   Email: {admin.email}")
            print(f"   Ativo: {admin.is_active}")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Erro ao criar admin:")
            print(f"   {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(create_admin())
