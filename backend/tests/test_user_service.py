"""
Teste manual do userService.

Valida:
- create_user
- get_user_by_id
- get_user_by_email
- update_user (email, password, is_active)
- delete_user (soft delete)
- Validação de email único
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.userService import (
    create_user,
    get_user_by_id,
    get_user_by_email,
    update_user,
    delete_user
)
from app.schemas.userSchema import UserCreate, UserUpdate


async def test_user_service():
    """Testa todas as operações do userService"""
    
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("TESTE 1: Criar usuário administrativo")
        print("=" * 60)
        
        try:
            user_data = UserCreate(
                email="admin@agencia.com",
                password="SenhaSegura123"
            )
            
            user = await create_user(user_data, db)
            
            print(f"✅ Usuário criado com sucesso!")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Ativo: {user.is_active}")
            print(f"   Hash (primeiros 20 chars): {user.hashed_password[:20]}...")
            print()
            
            user_id = user.id
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            return
        
        # ============================================
        print("=" * 60)
        print("TESTE 2: Buscar usuário por ID")
        print("=" * 60)
        
        found = await get_user_by_id(user_id, db)
        if found:
            print(f"✅ Usuário encontrado: {found.email}")
            print(f"   Ativo: {found.is_active}")
        else:
            print("❌ Usuário não encontrado")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 3: Buscar usuário por email")
        print("=" * 60)
        
        found_by_email = await get_user_by_email("admin@agencia.com", db)
        if found_by_email:
            print(f"✅ Usuário encontrado pelo email")
            print(f"   ID: {found_by_email.id}")
        else:
            print("❌ Usuário não encontrado")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 4: Atualizar email do usuário")
        print("=" * 60)
        
        try:
            update_data = UserUpdate(
                email="novo.admin@agencia.com"
            )
            
            updated = await update_user(user_id, update_data, db)
            
            print(f"✅ Email atualizado com sucesso!")
            print(f"   Novo email: {updated.email}")
        except Exception as e:
            print(f"❌ Erro ao atualizar email: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 5: Atualizar senha do usuário")
        print("=" * 60)
        
        try:
            old_hash = updated.hashed_password
            
            update_data = UserUpdate(
                password="NovaSenha456"
            )
            
            updated = await update_user(user_id, update_data, db)
            
            print(f"✅ Senha atualizada com sucesso!")
            print(f"   Hash anterior: {old_hash[:20]}...")
            print(f"   Novo hash: {updated.hashed_password[:20]}...")
            print(f"   Hashes diferentes: {old_hash != updated.hashed_password}")
        except Exception as e:
            print(f"❌ Erro ao atualizar senha: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 6: Desativar usuário via update")
        print("=" * 60)
        
        try:
            update_data = UserUpdate(
                is_active=False
            )
            
            updated = await update_user(user_id, update_data, db)
            
            print(f"✅ Usuário desativado!")
            print(f"   is_active: {updated.is_active}")
        except Exception as e:
            print(f"❌ Erro ao desativar: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 7: Reativar usuário")
        print("=" * 60)
        
        try:
            update_data = UserUpdate(
                is_active=True
            )
            
            updated = await update_user(user_id, update_data, db)
            
            print(f"✅ Usuário reativado!")
            print(f"   is_active: {updated.is_active}")
        except Exception as e:
            print(f"❌ Erro ao reativar: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 8: Criar segundo usuário")
        print("=" * 60)
        
        try:
            user2_data = UserCreate(
                email="admin2@agencia.com",
                password="senha123"
            )
            
            user2 = await create_user(user2_data, db)
            print(f"✅ Segundo usuário criado: {user2.email}")
            
            user2_id = user2.id
        except Exception as e:
            print(f"❌ Erro ao criar segundo usuário: {e}")
            user2_id = None
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 9: Validar email único (deve falhar)")
        print("=" * 60)
        
        try:
            duplicate = UserCreate(
                email="novo.admin@agencia.com",  # ❌ Email já existe
                password="senha456"
            )
            
            await create_user(duplicate, db)
            print("❌ ERRO: Deveria ter bloqueado email duplicado!")
        except ValueError as e:
            print(f"✅ Validação funcionou: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 10: Soft delete do usuário")
        print("=" * 60)
        
        try:
            deleted = await delete_user(user_id, db)
            
            print(f"✅ Usuário deletado (soft delete)!")
            print(f"   is_active: {deleted.is_active}")
            print(f"   Email ainda existe no banco: {deleted.email}")
        except Exception as e:
            print(f"❌ Erro ao deletar: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("CLEANUP: Deletar segundo usuário")
        print("=" * 60)
        
        if user2_id:
            await delete_user(user2_id, db)
            print(f"✅ Segundo usuário deletado")
        
        print()
        print("=" * 60)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_user_service())
