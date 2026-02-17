import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    """
    Usuário administrativo do sistema.
    
    Como apenas uma pessoa usa o sistema, todos os usuários são ADMIN.
    Mantido simples para facilitar manutenção.
    """
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True,
        comment="Email de login (único)"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        comment="Senha hasheada (bcrypt)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        comment="Se usuário está ativo no sistema"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
