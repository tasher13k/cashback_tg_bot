from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, DECIMAL, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from datetime import datetime
from .session import Base

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    telegram_id = Column(Integer, primary_key=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Связи
    bank_cards = relationship("BankCard", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id})>"

class Bank(Base):
    """Модель банка"""
    __tablename__ = 'banks'
    
    bank_id = Column(Integer, primary_key=True, autoincrement=True)
    bank_name = Column(String(100), unique=True, nullable=False)
    
    # Связи
    bank_cards = relationship("BankCard", back_populates="bank")
    categories = relationship("BankSpecificCategory", back_populates="bank", cascade="all, delete-orphan")
    
    @validates('bank_name')
    def validate_bank_name(self, key, bank_name):
        if not bank_name or len(bank_name.strip()) < 2:
            raise ValueError("Название банка должно содержать минимум 2 символа")
        return bank_name.strip()
    
    def __repr__(self):
        return f"<Bank(bank_id={self.bank_id}, name='{self.bank_name}')>"

class BankCard(Base):
    """Модель банковской карты"""
    __tablename__ = 'bank_cards'
    
    card_id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(Integer, ForeignKey('banks.bank_id', ondelete="CASCADE"), nullable=False)
    telegram_id = Column(Integer, ForeignKey('users.telegram_id', ondelete="CASCADE"), nullable=False)
    card_name = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)
    
    # Связи
    bank = relationship("Bank", back_populates="bank_cards")
    user = relationship("User", back_populates="bank_cards")
    active_categories = relationship("CardActiveCategory", back_populates="card", cascade="all, delete-orphan")
    
    @validates('card_name')
    def validate_card_name(self, key, card_name):
        if not card_name or len(card_name.strip()) < 1:
            raise ValueError("Название карты не может быть пустым")
        if len(card_name.strip()) > 100:
            raise ValueError("Название карты слишком длинное")
        return card_name.strip()
    
    def __repr__(self):
        return f"<BankCard(card_id={self.card_id}, name='{self.card_name}')>"

class MCCList(Base):
    """Модель MCC кодов"""
    __tablename__ = 'mcc_list'
    
    mcc = Column(Integer, primary_key=True, nullable=False)
    category_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Связи
    category_mappings = relationship("BankCategoryMapping", back_populates="mcc")
    
    def __repr__(self):
        return f"<MCCList(mcc={self.mcc}, name='{self.category_name}')>"

class BankSpecificCategory(Base):
    """Модель категорий конкретного банка"""
    __tablename__ = 'bank_specific_categories'
    
    bank_category_id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(Integer, ForeignKey('banks.bank_id', ondelete="CASCADE"), nullable=False)
    bank_category_name = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    bank = relationship("Bank", back_populates="categories")
    category_mappings = relationship("BankCategoryMapping", back_populates="bank_category", cascade="all, delete-orphan")
    active_categories = relationship("CardActiveCategory", back_populates="bank_category")
    
    @validates('bank_category_name')
    def validate_category_name(self, key, category_name):
        if not category_name or len(category_name.strip()) < 1:
            raise ValueError("Название категории не может быть пустым")
        return category_name.strip()
    
    def __repr__(self):
        return f"<BankSpecificCategory(id={self.bank_category_id}, name='{self.bank_category_name}')>"

class BankCategoryMapping(Base):
    """Связь между MCC кодами и категориями банка"""
    __tablename__ = 'bank_category_mapping'
    
    bank_category_id = Column(Integer, ForeignKey('bank_specific_categories.bank_category_id', ondelete="CASCADE"), primary_key=True)
    mcc = Column(Integer, ForeignKey('mcc_list.mcc', ondelete="CASCADE"), primary_key=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    bank_category = relationship("BankSpecificCategory", back_populates="category_mappings")
    mcc_record = relationship("MCCList", back_populates="category_mappings")
    
    def __repr__(self):
        return f"<BankCategoryMapping(bank_category_id={self.bank_category_id}, mcc={self.mcc})>"

class CardActiveCategory(Base):
    """Активные категории кэшбэка для карты"""
    __tablename__ = 'card_active_categories'
    
    card_category_id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(Integer, ForeignKey('bank_cards.card_id', ondelete="CASCADE"), nullable=False)
    bank_category_id = Column(Integer, ForeignKey('bank_specific_categories.bank_category_id', ondelete="CASCADE"), nullable=False)
    valid_to = Column(DateTime, nullable=True)  # Для сезонных кэшбеков
    cashback_percentage = Column(DECIMAL(5, 2), nullable=False)  # 999.99% максимум
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Связи
    card = relationship("BankCard", back_populates="active_categories")
    bank_category = relationship("BankSpecificCategory", back_populates="active_categories")
    
    @validates('cashback_percentage')
    def validate_percentage(self, key, percentage):
        if percentage < 0 or percentage > 1000:  # 1000% максимум
            raise ValueError("Процент кэшбэка должен быть от 0 до 1000")
        return percentage
    
    def is_active(self) -> bool:
        """Проверка активности категории (не истек срок)"""
        if self.valid_to is None:
            return True
        return datetime.now() < self.valid_to
    
    def __repr__(self):
        return f"<CardActiveCategory(id={self.card_category_id}, card_id={self.card_id}, percentage={self.cashback_percentage})>"