from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os

# Базовый класс для моделей
Base = declarative_base()

class DatabaseSession:
    """Управление сессиями базы данных"""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            class_=Session
        )
        
    def create_tables(self):
        """Создание всех таблиц"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Получение сессии"""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """Закрытие сессии"""
        session.close()
    
    # Контекстный менеджер для сессий
    def session(self):
        """Использование как контекстный менеджер"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Создаем глобальный экземпляр
db_session = DatabaseSession()