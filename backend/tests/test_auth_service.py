"""
Teste manual do authService.

Valida:
- hash_password
- verify_password
- authenticate_user
- create_access_token (sem role)
- verify_token
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.authService import (
    hash_password,
    verify_password,
    authenticate_user,
    create_access_token,
    verify_token
)
from app.services.userService import create_user, delete_user
from app.schemas.userSchema import UserCreate


async def test_auth_service():
    """Testa todas as operações do authService"""
    
    print("=" * 60)
    print("TESTE 1: Hash de senha (bcrypt)")
    print("=" * 60)
    
    password = "minha_senha_super_segura_123"
    hashed = hash_password(password)
    
    print(f"✅ Hash gerado com sucesso!")
    print(f"   Senha original: {password}")
    print(f"   Hash (primeiros 30 chars): {hashed[:30]}...")
    print(f"   Tamanho do hash: {len(hashed)} caracteres")
    print()
    
    # ============================================
    print("=" * 60)
    print("TESTE 2: Verificar senha (bcrypt)")
    print("=" * 60)
    
    is_valid = verify_password(password, hashed)
    print(f"✅ Senha correta verificada: {is_valid}")
    
    is_invalid = verify_password("senha_errada", hashed)
    print(f"✅ Senha incorreta detectada: {not is_invalid}")
    print()
    
    # ============================================
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("SETUP: Criar usuário para testes de autenticação")
        print("=" * 60)
        
        try:
            user_data = UserCreate(
                email="test.auth@agencia.com",
                password="senha_teste_auth_789"
            )
            
            user = await create_user(user_data, db)
            print(f"✅ Usuário criado: {user.email}")
            print()
            
            user_id = user.id
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            return
        
        # ============================================
        print("=" * 60)
        print("TESTE 3: Autenticar usuário (credenciais corretas)")
        print("=" * 60)
        
        try:
            authenticated = await authenticate_user(
                "test.auth@agencia.com",
                "senha_teste_auth_789",
                db
            )
            
            print(f"✅ Autenticação bem-sucedida!")
            print(f"   Email: {authenticated.email}")
            print(f"   ID: {authenticated.id}")
            print(f"   Ativo: {authenticated.is_active}")
        except ValueError as e:
            print(f"❌ Erro na autenticação: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 4: Autenticar com senha incorreta (deve falhar)")
        print("=" * 60)
        
        try:
            await authenticate_user(
                "test.auth@agencia.com",
                "senha_errada",  # ❌ Senha incorreta
                db
            )
            print("❌ ERRO: Deveria ter rejeitado senha incorreta!")
        except ValueError as e:
            print(f"✅ Validação funcionou: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 5: Autenticar com email inexistente (deve falhar)")
        print("=" * 60)
        
        try:
            await authenticate_user(
                "email.nao.existe@agencia.com",  # ❌ Email inexistente
                "qualquer_senha",
                db
            )
            print("❌ ERRO: Deveria ter rejeitado email inexistente!")
        except ValueError as e:
            print(f"✅ Validação funcionou: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 6: Criar token JWT (sem role)")
        print("=" * 60)
        
        token = create_access_token(user.id)
        
        print(f"✅ Token JWT criado!")
        print(f"   Token (primeiros 50 chars): {token[:50]}...")
        print(f"   Tamanho total: {len(token)} caracteres")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 7: Verificar e decodificar token")
        print("=" * 60)
        
        try:
            payload = verify_token(token)
            
            print(f"✅ Token válido e decodificado!")
            print(f"   user_id (sub): {payload['sub']}")
            print(f"   user_id original: {user.id}")
            print(f"   IDs coincidem: {payload['sub'] == str(user.id)}")
            print(f"   Chaves no payload: {list(payload.keys())}")
            
            # Verificar se role NÃO está no payload
            if 'role' in payload:
                print(f"   ❌ ERRO: Campo 'role' ainda está no payload!")
            else:
                print(f"   ✅ Campo 'role' removido corretamente do payload")
            
        except ValueError as e:
            print(f"❌ Erro ao verificar token: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 8: Criar token com duração customizada")
        print("=" * 60)
        
        long_token = create_access_token(user.id, expires_delta_minutes=10080)  # 7 dias
        
        print(f"✅ Token de longa duração criado!")
        print(f"   Duração: 7 dias (10080 minutos)")
        
        payload_long = verify_token(long_token)
        print(f"   Token válido: {payload_long['sub'] == str(user.id)}")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 9: Verificar token inválido (deve falhar)")
        print("=" * 60)
        
        try:
            fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.token"
            verify_token(fake_token)
            print("❌ ERRO: Deveria ter rejeitado token inválido!")
        except ValueError as e:
            print(f"✅ Validação funcionou: Token inválido detectado")
        print()
        
        # ============================================
        print("=" * 60)
        print("TESTE 10: Desativar usuário e tentar autenticar")
        print("=" * 60)
        
        # Desativar usuário
        from app.schemas.userSchema import UserUpdate
        from app.services.userService import update_user
        
        await update_user(user_id, UserUpdate(is_active=False), db)
        print("   Usuário desativado")
        
        try:
            await authenticate_user(
                "test.auth@agencia.com",
                "senha_teste_auth_789",
                db
            )
            print("❌ ERRO: Deveria ter bloqueado usuário inativo!")
        except ValueError as e:
            print(f"✅ Validação funcionou: {e}")
        print()
        
        # ============================================
        print("=" * 60)
        print("CLEANUP: Deletar usuário de teste")
        print("=" * 60)
        
        await delete_user(user_id, db)
        print(f"✅ Usuário deletado")
        
        print()
        print("=" * 60)
        print("✅ TODOS OS TESTES CONCLUÍDOS!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_auth_service())
