from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .repository import (
    UserRepository, BankRepository, CardRepository,
    CategoryRepository, MCCRepository
)

class DatabaseService:
    """Основной сервис для работы с базой данных"""
    
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.banks = BankRepository(session)
        self.cards = CardRepository(session)
        self.categories = CategoryRepository(session)
        self.mcc = MCCRepository(session)
    
    # ========== ПОЛЬЗОВАТЕЛИ ==========
    
    def ensure_user_exists(self, telegram_id: int) -> bool:
        """Убедиться, что пользователь существует"""
        return self.users.user_exists(telegram_id)
    
    # ========== БАНКИ ==========
    
    def get_all_banks(self) -> List[Dict[str, Any]]:
        """Получить список всех банков"""
        banks = self.banks.get_all_banks()
        return [{'id': b.bank_id, 'name': b.bank_name} for b in banks]
    
    def get_bank_categories(self, bank_id: int) -> List[Dict[str, Any]]:
        """Получить категории банка"""
        categories = self.banks.get_bank_categories(bank_id)
        return [
            {
                'id': c.bank_category_id,
                'name': c.bank_category_name,
                'updated_at': c.updated_at
            }
            for c in categories
        ]
    
    # ========== КАРТЫ ==========
    
    def add_user_card(
        self,
        telegram_id: int,
        bank_id: int,
        card_name: str,
        comment: str = None
    ) -> Dict[str, Any]:
        """Добавить карту пользователю"""
        # Создаем пользователя, если не существует
        self.users.get_or_create_user(telegram_id)
        
        # Добавляем карту
        card = self.cards.add_card(telegram_id, bank_id, card_name, comment)
        
        return {
            'id': card.card_id,
            'name': card.card_name,
            'bank_id': card.bank_id,
            'bank_name': card.bank.bank_name,
            'comment': card.comment
        }
    
    def get_user_cards(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Получить все карты пользователя с категориями"""
        cards = self.cards.get_user_cards(telegram_id)
        
        result = []
        for card in cards:
            active_categories = self.categories.get_active_cashbacks(card.card_id)
            
            result.append({
                'id': card.card_id,
                'name': card.card_name,
                'bank': card.bank.bank_name,
                'comment': card.comment,
                'cashbacks': active_categories,
                'categories_count': len(active_categories)
            })
        
        return result
    
    def update_card_name(self, card_id: int, new_name: str) -> Dict[str, Any]:
        """Изменить название карты"""
        card = self.cards.update_card_name(card_id, new_name)
        
        return {
            'id': card.card_id,
            'old_name': card.card_name,  # SQLAlchemy уже обновил объект
            'new_name': new_name,
            'bank_name': card.bank.bank_name
        }
    
    def delete_user_card(self, card_id: int) -> bool:
        """Удалить карту"""
        return self.cards.delete_card(card_id)
    
    # ========== КЭШБЭКИ ==========
    
    def add_cashback_to_card(
        self,
        card_id: int,
        categories_dict: Dict[str, float],
        valid_days: int = None
    ) -> Dict[str, Any]:
        """
        Добавить кэшбэк к карте
        
        categories_dict: {"Категория": процент}
        valid_days: срок действия в днях (опционально)
        """
        valid_to = None
        if valid_days:
            valid_to = datetime.now() + timedelta(days=valid_days)
        
        added_categories = self.categories.add_cashback_categories(
            card_id, categories_dict, valid_to
        )
        
        # Получаем информацию о карте для ответа
        card = self.cards.get_card_by_id(card_id)
        
        return {
            'card_id': card_id,
            'card_name': card.card_name,
            'bank_name': card.bank.bank_name,
            'added_categories': [
                {
                    'name': cat.bank_category.bank_category_name,
                    'percentage': float(cat.cashback_percentage),
                    'valid_to': cat.valid_to
                }
                for cat in added_categories
            ]
        }
    
    def remove_cashback_category(self, card_id: int, category_name: str) -> bool:
        """Удалить категорию кэшбэка у карты"""
        return self.categories.remove_cashback_category(card_id, category_name)
    
    def clear_card_cashbacks(self, card_id: int) -> int:
        """Очистить все кэшбэки карты"""
        return self.categories.remove_all_cashback_categories(card_id)
    
    def get_card_cashbacks(self, card_id: int) -> Dict[str, Any]:
        """Получить все кэшбэки карты"""
        card = self.cards.get_card_with_categories(card_id)
        if not card:
            return {}
        
        active_categories = []
        expired_categories = []
        
        for active_cat in card.active_categories:
            category_info = {
                'id': active_cat.bank_category.bank_category_id,
                'name': active_cat.bank_category.bank_category_name,
                'percentage': float(active_cat.cashback_percentage),
                'updated_at': active_cat.updated_at,
                'valid_to': active_cat.valid_to
            }
            
            if active_cat.is_active():
                active_categories.append(category_info)
            else:
                expired_categories.append(category_info)
        
        return {
            'card_id': card.card_id,
            'card_name': card.card_name,
            'bank_name': card.bank.bank_name,
            'active_cashbacks': active_categories,
            'expired_cashbacks': expired_categories,
            'total_active': len(active_categories),
            'total_expired': len(expired_categories)
        }
    
    # ========== ПОИСК ЛУЧШЕЙ КАРТЫ ==========
    
    def find_best_card_for_purchase(
        self,
        telegram_id: int,
        category_name: str,
        amount: float = None
    ) -> Dict[str, Any]:
        """Найти лучшую карту для покупки в категории"""
        result = self.categories.find_best_card_for_category(
            telegram_id, category_name, amount
        )
        
        if not result[0]:
            return {'found': False}
        
        card, cashback = result
        
        response = {
            'found': True,
            'card': {
                'id': card.card_id,
                'name': card.card_name,
                'bank': card.bank.bank_name
            },
            'category': category_name
        }
        
        if amount:
            percentage = (cashback / amount) * 100 if amount > 0 else 0
            response.update({
                'amount': amount,
                'cashback_amount': cashback,
                'cashback_percentage': round(percentage, 2)
            })
        else:
            response['cashback_percentage'] = cashback
        
        return response
    
    # ========== СТАТИСТИКА ==========
    
    def get_user_statistics(self, telegram_id: int) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        cards = self.cards.get_user_cards(telegram_id)
        
        if not cards:
            return {'total_cards': 0, 'total_cashbacks': 0}
        
        total_cashbacks = 0
        total_active_cashbacks = 0
        
        for card in cards:
            cashbacks = self.categories.get_active_cashbacks(card.card_id)
            total_cashbacks += len(cashbacks)
            total_active_cashbacks += sum(1 for p in cashbacks.values() if p > 0)
        
        return {
            'total_cards': len(cards),
            'total_cashbacks': total_cashbacks,
            'total_active_cashbacks': total_active_cashbacks,
            'avg_cashbacks_per_card': round(total_cashbacks / len(cards), 2) if cards else 0
        }