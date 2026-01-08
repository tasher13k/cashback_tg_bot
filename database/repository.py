from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, select, delete, update
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import logging
from .models import (
    User, Bank, BankCard, MCCList,
    BankSpecificCategory, BankCategoryMapping, CardActiveCategory
)

logger = logging.getLogger(__name__)

class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_or_create_user(self, telegram_id: int) -> User:
        """Получить или создать пользователя"""
        user = self.session.get(User, telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            self.session.flush()
            logger.info(f"Создан новый пользователь: {telegram_id}")
        return user
    
    def user_exists(self, telegram_id: int) -> bool:
        """Проверить существование пользователя"""
        return self.session.get(User, telegram_id) is not None

class BankRepository:
    """Репозиторий для работы с банками"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_all_banks(self) -> List[Bank]:
        """Получить все банки"""
        return self.session.query(Bank).order_by(Bank.bank_name).all()
    
    def get_bank_by_id(self, bank_id: int) -> Optional[Bank]:
        """Получить банк по ID"""
        return self.session.get(Bank, bank_id)
    
    def get_bank_by_name(self, bank_name: str) -> Optional[Bank]:
        """Получить банк по названию"""
        return self.session.query(Bank).filter(Bank.bank_name == bank_name).first()
    
    def create_bank(self, bank_name: str) -> Bank:
        """Создать новый банк"""
        bank = Bank(bank_name=bank_name)
        self.session.add(bank)
        self.session.flush()
        logger.info(f"Создан новый банк: {bank_name}")
        return bank
    
    def get_bank_categories(self, bank_id: int) -> List[BankSpecificCategory]:
        """Получить все категории банка"""
        return self.session.query(BankSpecificCategory)\
            .filter(BankSpecificCategory.bank_id == bank_id)\
            .order_by(BankSpecificCategory.bank_category_name)\
            .all()
    
    def get_category_by_name(self, bank_id: int, category_name: str) -> Optional[BankSpecificCategory]:
        """Найти категорию по названию у конкретного банка"""
        return self.session.query(BankSpecificCategory)\
            .filter(
                and_(
                    BankSpecificCategory.bank_id == bank_id,
                    BankSpecificCategory.bank_category_name == category_name
                )
            ).first()

class CardRepository:
    """Репозиторий для работы с картами"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_card(self, telegram_id: int, bank_id: int, card_name: str, comment: str = None) -> BankCard:
        """Добавить новую карту"""
        # Проверяем существование пользователя
        user = self.session.get(User, telegram_id)
        if user is None:
            raise ValueError(f"Пользователь {telegram_id} не найден")
        
        # Проверяем существование банка
        bank = self.session.get(Bank, bank_id)
        if bank is None:
            raise ValueError(f"Банк с ID {bank_id} не найден")
        
        # Проверяем, нет ли уже карты с таким именем у пользователя
        existing_card = self.session.query(BankCard)\
            .filter(
                and_(
                    BankCard.telegram_id == telegram_id,
                    BankCard.card_name == card_name,
                    BankCard.bank_id == bank_id
                )
            ).first()
        
        if existing_card:
            raise ValueError(f"Карта '{card_name}' уже существует у пользователя")
        
        # Создаем карту
        card = BankCard(
            telegram_id=telegram_id,
            bank_id=bank_id,
            card_name=card_name,
            comment=comment
        )
        
        self.session.add(card)
        self.session.flush()
        logger.info(f"Добавлена карта: {card_name} для пользователя {telegram_id}")
        
        return card
    
    def get_user_cards(self, telegram_id: int) -> List[BankCard]:
        """Получить все карты пользователя с информацией о банке"""
        return self.session.query(BankCard)\
            .options(joinedload(BankCard.bank))\
            .filter(BankCard.telegram_id == telegram_id)\
            .order_by(BankCard.card_name)\
            .all()
    
    def get_card_by_id(self, card_id: int) -> Optional[BankCard]:
        """Получить карту по ID со всеми связями"""
        return self.session.query(BankCard)\
            .options(
                joinedload(BankCard.bank),
                joinedload(BankCard.active_categories).joinedload(CardActiveCategory.bank_category)
            )\
            .filter(BankCard.card_id == card_id)\
            .first()
    
    def update_card_name(self, card_id: int, new_name: str) -> BankCard:
        """Изменить название карты"""
        card = self.session.get(BankCard, card_id)
        if card is None:
            raise ValueError(f"Карта с ID {card_id} не найдена")
        
        # Проверяем уникальность нового имени
        existing = self.session.query(BankCard)\
            .filter(
                and_(
                    BankCard.telegram_id == card.telegram_id,
                    BankCard.card_name == new_name,
                    BankCard.bank_id == card.bank_id,
                    BankCard.card_id != card_id
                )
            ).first()
        
        if existing:
            raise ValueError(f"Карта с названием '{new_name}' уже существует")
        
        card.card_name = new_name
        self.session.flush()
        logger.info(f"Обновлено название карты {card_id}: {new_name}")
        
        return card
    
    def delete_card(self, card_id: int) -> bool:
        """Удалить карту (каскадно удалятся все связанные категории)"""
        card = self.session.get(BankCard, card_id)
        if card is None:
            return False
        
        self.session.delete(card)
        self.session.flush()
        logger.info(f"Удалена карта {card_id}")
        return True
    
    def get_card_with_categories(self, card_id: int) -> Optional[BankCard]:
        """Получить карту со всеми активными категориями"""
        return self.session.query(BankCard)\
            .options(
                joinedload(BankCard.bank),
                joinedload(BankCard.active_categories)
                .joinedload(CardActiveCategory.bank_category)
            )\
            .filter(BankCard.card_id == card_id)\
            .first()

class CategoryRepository:
    """Репозиторий для работы с категориями кэшбэка"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_cashback_categories(
        self,
        card_id: int,
        categories_dict: Dict[str, float],
        valid_to: datetime = None
    ) -> List[CardActiveCategory]:
        """
        Добавить категории кэшбэка к карте
        
        categories_dict: {"Название категории": процент_кэшбэка}
        """
        # Получаем карту
        card = self.session.get(BankCard, card_id)
        if card is None:
            raise ValueError(f"Карта с ID {card_id} не найдена")
        
        # Получаем все категории банка
        bank_categories = self.session.query(BankSpecificCategory)\
            .filter(BankSpecificCategory.bank_id == card.bank_id)\
            .all()
        
        # Создаем словарь для быстрого поиска по названию
        category_map = {cat.bank_category_name.lower(): cat for cat in bank_categories}
        
        added_categories = []
        
        for category_name, percentage in categories_dict.items():
            # Ищем категорию в списке категорий банка
            category_key = category_name.lower()
            bank_category = category_map.get(category_key)
            
            if not bank_category:
                raise ValueError(
                    f"Категория '{category_name}' не найдена в списке категорий банка {card.bank.bank_name}.\n"
                    f"Доступные категории: {', '.join([c.bank_category_name for c in bank_categories])}"
                )
            
            # Проверяем, нет ли уже такой категории у карты
            existing = self.session.query(CardActiveCategory)\
                .filter(
                    and_(
                        CardActiveCategory.card_id == card_id,
                        CardActiveCategory.bank_category_id == bank_category.bank_category_id
                    )
                ).first()
            
            if existing:
                # Обновляем существующую категорию
                existing.cashback_percentage = percentage
                existing.valid_to = valid_to
                existing.updated_at = datetime.now()
                added_categories.append(existing)
                logger.info(f"Обновлена категория {category_name} для карты {card_id}")
            else:
                # Создаем новую категорию
                active_category = CardActiveCategory(
                    card_id=card_id,
                    bank_category_id=bank_category.bank_category_id,
                    cashback_percentage=percentage,
                    valid_to=valid_to
                )
                self.session.add(active_category)
                added_categories.append(active_category)
                logger.info(f"Добавлена категория {category_name} для карты {card_id}")
        
        self.session.flush()
        return added_categories
    
    def remove_cashback_category(self, card_id: int, category_name: str) -> bool:
        """Удалить категорию кэшбэка у карты"""
        # Находим ID категории банка по названию
        bank_category = self.session.query(BankSpecificCategory)\
            .join(BankCard, BankCard.bank_id == BankSpecificCategory.bank_id)\
            .filter(
                and_(
                    BankCard.card_id == card_id,
                    BankSpecificCategory.bank_category_name == category_name
                )
            ).first()
        
        if not bank_category:
            return False
        
        # Удаляем активную категорию
        deleted_count = self.session.query(CardActiveCategory)\
            .filter(
                and_(
                    CardActiveCategory.card_id == card_id,
                    CardActiveCategory.bank_category_id == bank_category.bank_category_id
                )
            ).delete()
        
        self.session.flush()
        
        if deleted_count > 0:
            logger.info(f"Удалена категория {category_name} у карты {card_id}")
            return True
        
        return False
    
    def remove_all_cashback_categories(self, card_id: int) -> int:
        """Удалить все категории кэшбэка у карты"""
        deleted_count = self.session.query(CardActiveCategory)\
            .filter(CardActiveCategory.card_id == card_id)\
            .delete()
        
        self.session.flush()
        logger.info(f"Удалены все категории у карты {card_id}")
        return deleted_count
    
    def get_card_categories(self, card_id: int) -> List[CardActiveCategory]:
        """Получить все активные категории карты"""
        return self.session.query(CardActiveCategory)\
            .options(joinedload(CardActiveCategory.bank_category))\
            .filter(CardActiveCategory.card_id == card_id)\
            .all()
    
    def get_active_cashbacks(self, card_id: int) -> Dict[str, float]:
        """Получить словарь активных кэшбэков карты (только активные)"""
        categories = self.session.query(
            BankSpecificCategory.bank_category_name,
            CardActiveCategory.cashback_percentage
        )\
            .join(CardActiveCategory, CardActiveCategory.bank_category_id == BankSpecificCategory.bank_category_id)\
            .filter(
                and_(
                    CardActiveCategory.card_id == card_id,
                    or_(
                        CardActiveCategory.valid_to.is_(None),
                        CardActiveCategory.valid_to > datetime.now()
                    )
                )
            )\
            .all()
        
        return {name: float(percentage) for name, percentage in categories}
    
    def find_best_card_for_category(
        self,
        telegram_id: int,
        category_name: str,
        amount: float = None
    ) -> Tuple[Optional[BankCard], Optional[float]]:
        """Найти лучшую карту для категории"""
        # Ищем категорию среди всех категорий банков пользователя
        result = self.session.query(
            BankCard,
            CardActiveCategory.cashback_percentage
        )\
            .join(CardActiveCategory, CardActiveCategory.card_id == BankCard.card_id)\
            .join(BankSpecificCategory, BankSpecificCategory.bank_category_id == CardActiveCategory.bank_category_id)\
            .filter(
                and_(
                    BankCard.telegram_id == telegram_id,
                    BankSpecificCategory.bank_category_name == category_name,
                    or_(
                        CardActiveCategory.valid_to.is_(None),
                        CardActiveCategory.valid_to > datetime.now()
                    )
                )
            )\
            .order_by(CardActiveCategory.cashback_percentage.desc())\
            .first()
        
        if not result:
            return None, None
        
        card, percentage = result
        
        if amount:
            cashback_amount = amount * (float(percentage) / 100)
            return card, cashback_amount
        
        return card, float(percentage)

class MCCRepository:
    """Репозиторий для работы с MCC кодами"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def map_category_to_mcc(self, bank_category_id: int, mcc_codes: List[int]) -> List[BankCategoryMapping]:
        """Связать категорию банка с MCC кодами"""
        mappings = []
        
        for mcc in mcc_codes:
            # Проверяем существование MCC кода
            mcc_record = self.session.get(MCCList, mcc)
            if not mcc_record:
                raise ValueError(f"MCC код {mcc} не найден")
            
            # Проверяем, нет ли уже такой связи
            existing = self.session.query(BankCategoryMapping)\
                .filter(
                    and_(
                        BankCategoryMapping.bank_category_id == bank_category_id,
                        BankCategoryMapping.mcc == mcc
                    )
                ).first()
            
            if not existing:
                mapping = BankCategoryMapping(
                    bank_category_id=bank_category_id,
                    mcc=mcc
                )
                self.session.add(mapping)
                mappings.append(mapping)
        
        self.session.flush()
        return mappings
    
    def get_mcc_for_category(self, bank_category_id: int) -> List[MCCList]:
        """Получить все MCC коды для категории банка"""
        return self.session.query(MCCList)\
            .join(BankCategoryMapping, BankCategoryMapping.mcc == MCCList.mcc)\
            .filter(BankCategoryMapping.bank_category_id == bank_category_id)\
            .all()
    
    def get_category_for_mcc(self, mcc: int, bank_id: int) -> Optional[BankSpecificCategory]:
        """Получить категорию банка для MCC кода"""
        return self.session.query(BankSpecificCategory)\
            .join(BankCategoryMapping, BankCategoryMapping.bank_category_id == BankSpecificCategory.bank_category_id)\
            .filter(
                and_(
                    BankCategoryMapping.mcc == mcc,
                    BankSpecificCategory.bank_id == bank_id
                )
            ).first()