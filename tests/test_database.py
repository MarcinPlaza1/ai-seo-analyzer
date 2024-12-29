import pytest
import pytest_asyncio
from typing import Dict, Any, List, Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect
from app.core.database import get_db, Base, engine
from app.models.user import User
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

@pytest.mark.asyncio
async def test_database_connection_error() -> None:
    """Test obsługi błędu połączenia z bazą danych"""
    with patch('app.core.database.engine') as mock_engine:
        mock_engine.connect.side_effect = SQLAlchemyError("Connection error")
        
        with pytest.raises(SQLAlchemyError) as exc_info:
            db = next(get_db())
        
        assert "Connection error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_database_session_cleanup(test_db: Session) -> None:
    """Test czyszczenia sesji bazy danych"""
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password"
    )
    test_db.add(user)
    test_db.commit()

    added_user = test_db.query(User).filter_by(email="test@example.com").first()
    assert added_user is not None

    test_db.close()

    with pytest.raises(Exception) as exc_info:
        test_db.query(User).all()
    
    assert "closed" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_database_transaction_rollback(test_db: Session) -> None:
    """Test wycofywania transakcji"""
    try:
        user1 = User(
            email="user1@example.com",
            full_name="User 1",
            hashed_password="hashed_password"
        )
        test_db.add(user1)
        test_db.flush()

        user2 = User(
            email="user1@example.com",
            full_name="User 2",
            hashed_password="hashed_password"
        )
        test_db.add(user2)
        test_db.commit()
    except SQLAlchemyError:
        test_db.rollback()

    users = test_db.query(User).filter_by(email="user1@example.com").all()
    assert len(users) == 0

@pytest.mark.asyncio
async def test_database_connection_pool() -> None:
    """Test puli połączeń do bazy danych"""
    connections: List[Session] = []
    for _ in range(5):
        db = next(get_db())
        connections.append(db)

    for db in connections:
        assert not db.closed

    for db in connections:
        db.close()

    for db in connections:
        assert db.closed

@pytest.mark.asyncio
async def test_database_migration(test_db: Session) -> None:
    """Test migracji schematu bazy danych"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ["users", "audits", "audit_pages"]
    for table in required_tables:
        assert table in tables

    columns = {col['name'] for col in inspector.get_columns("users")}
    required_columns = {"id", "email", "full_name", "hashed_password", "is_active"}
    assert required_columns.issubset(columns) 