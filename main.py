from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, CallbackContext
#from telegram.ext import PicklePersistence
import os # for tg-token
import ocr_openrouter

# Состояния для ConversationHandler
ADD_CARD_2, ADD_CARD_3, ADD_CASHBACK_2, ADD_CASHBACK_3, EDIT_CARD_2, EDIT_CARD_3, EDIT_CARD_4 = range(7)

class Card:
    """Модель данных карты"""
    def __init__(self, bank_name, card_name):
        self.bank = bank_name
        self.name = card_name
        self.cashback_dict = {}

# Пример баз данных
banks = ["Сбербанк", "Тинькофф", "ВТБ", "Альфа-Банк"] 

def get_user_cards(context: ContextTypes.DEFAULT_TYPE):
    if 'cards' not in context.user_data:
        context.user_data['cards'] = []
    return context.user_data['cards']

# Обработчики команд
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён!")
    #context.user_data.clear()
    return ConversationHandler.END

# Функция старта
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    await update.message.reply_text("Привет! Я твой бот для управления картами и кэшбэками.\nИспользуй команду /help, чтобы узнать, что я могу!")

# Функция помощи
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("/start - Начало работы\n"
                              "/help - Помощь\n"
                              "/add_card - Добавить карту\n"
                              "/add_cashback - Добавить кэшбэк\n"
                              "/edit_card - Редактировать карту\n"
                              "/card_list - Список карт")
    
def suggest_add_card():
    message = "У вас пока нет карт, добавьте хотя бы одну через /add_card"
    return message

# Список карт пользователя
async def card_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #restore_state(update, context)
    card_list = get_user_cards(context)
    
    if card_list == []:
        message = suggest_add_card()
    else:
        message = "Ваши карты:\n\n"
        for card in card_list:
            message += f"Название: {card.name}\n"
            message += f"Банк: {card.bank}\n"
            for category, percent in card.cashback_dict.items():
                message += f"  - {category}: {percent}%\n"
            message += "\n"
    
    await update.message.reply_text(message)

# Функция добавления карты
async def add_card_1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global banks
    #restore_state(update, context)
    
    keyboard = [[InlineKeyboardButton(bank, callback_data=bank)] for bank in banks]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите банк для вашей карты:", reply_markup=reply_markup)

    # сохраняем состояние
    #context.user_data['state'] = ADD_CARD
    #store_state(update, context, ADD_CARD_NAME)
    return ADD_CARD_2

# Функция обработки выбора банка и ввода названия карты
async def add_card_2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #restore_state(update, context)
    query = update.callback_query
    context.user_data['bank_for_adding_card'] = query.data  # Сохраняем выбранный банк
    await query.answer()

    await query.edit_message_text(text=f"Вы выбрали банк {query.data}. Пожалуйста, введите название карты.")

    #context.user_data['state'] = ADD_CARD_NAME
    #store_state(update, context, SAVE_NEW_CARD)
    return ADD_CARD_3

async def add_card_3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #restore_state(update, context)

    context.user_data['name_for_adding_card'] = update.message.text # временно сохраняем введенное название карты
    
    card_list = save_card_in_list(context)
    await update.message.reply_text(f"Сохранена карта '{card_list[-1].name}' банка {card_list[-1].bank}.\n" \
                                    "Для просмотра всех карт и категорий введите /card_list")
    #context.user_data.clear()
    return ConversationHandler.END

def save_card_in_list(context: ContextTypes.DEFAULT_TYPE):
    card_list = get_user_cards(context)

    bank_name = context.user_data['bank_for_adding_card']
    card_name = context.user_data['name_for_adding_card']
    card_list.append(Card(bank_name, card_name))
    return card_list
    #context.user_data.clear()

# обработчик этапов добавления карты
add_card_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add_card", add_card_1_handler)], #add_card_2 - name, add_card_3 - save
    states={
        ADD_CARD_2: [CallbackQueryHandler(add_card_2_handler)], # обрабатываем нажатие на банк и предлагаем ввести имя карты
        ADD_CARD_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_card_3_handler), # обрабатываем имя карты и сохраняем
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
    )

# Функция добавления категорий кэшбэка к карте
async def add_cashback_1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    card_list = get_user_cards(context)
    #restore_state(update, context)

    if card_list == []:
        message = suggest_add_card()
        await update.message.reply_text(message)
        return ConversationHandler.END
    else:
        keyboard = [[InlineKeyboardButton(card.name, callback_data=i)] for i, card in enumerate(card_list)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "Выберите карту для добавления категорий:"
        await update.message.reply_text(message, reply_markup=reply_markup)    
    # сохраняем состояние
    #context.user_data['state'] = ADD_CASHBACK
    #store_state(update, context, CHOOSE_CARD_CASHBACK)
    return ADD_CASHBACK_2

# Функция обработки выбранного банка и предложение ввести название карты
async def add_cashback_2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #restore_state(update, context)
    query = update.callback_query
    context.user_data['card_index'] = int(query.data)  # Сохраняем номер выбранной карты из card_list
    await query.answer()

    await query.edit_message_text("Отлично! Теперь добавьте категории через список или скриншот."
                              "Введите категорию и число, например: 'Еда 5'. "
                              "Если категорий несколько, введите их через новую строку.")

    return ADD_CASHBACK_3

async def add_cashback_3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #restore_state(update, context)
    try:
        card_name = assign_categories_to_card(update.message.text, context) # присваиваем карте список кэшбэков от пользователя 
        await update.message.reply_text(f"Карте {card_name} присвоен список кэшбэков.\n"\
                                    "Для просмотра всех карт и категорий введите /card_list")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(str(e))
    #context.user_data.clear()

def make_cashlist_from_message(text: str) -> dict:
    '''Преобразует текст вида "Категория процент\n" в словарь {категория: процент}.'''
    # Проверка типа входного аргумента
    if not isinstance(text, str):
        raise TypeError(f"Ожидалась строка, получено {type(text).__name__}")
    
    categories = {}
    
    # Разбиваем текст на строки и обрабатываем каждую
    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()
        
        # Пропускаем пустые строки
        if not line:
            continue
            
        try:
            # Разделяем строку на категорию и сумму (по последнему пробелу)
            parts = line.rsplit(' ', 1)
            if len(parts) != 2:
                raise ValueError(f"Не найдено разделение на категорию и сумму")
                
            category, amount_str = parts
            
            # Проверяем, что категория не пустая
            if not category:
                raise ValueError(f"Пустая категория")
                
            # Преобразуем сумму в число
            try:
                # Сначала пытаемся как int, потом как float
                if '.' in amount_str:
                    amount = float(amount_str)
                else:
                    amount = int(amount_str)
            except ValueError:
                raise ValueError(
                    f"Невалидное число '{amount_str}' в сумме"
                )
                
            # Проверяем, что сумма положительная
            if (amount <= 0) or (amount > 100) :
                raise ValueError(
                    f"Процент кэшбэка должен быть в диапазоне (0, 100]! ({amount})"
                )
                
            # Добавляем в словарь
            categories[category] = amount
            
        except ValueError as e:
            # Перехватываем и переформулируем все ошибки с указанием номера строки
            raise ValueError(f"Ошибка в строке {line_num}:\n{str(e)}\nВведите список кэшбэков заново.") from e
    
    return categories
         
def assign_categories_to_card(categoies: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    card_index = context.user_data['card_index']
    card_list = get_user_cards(context)
    card_list[card_index].cashback_dict = make_cashlist_from_message(categoies) # присваиваем карте словарь кэшбэков от пользователя
    return card_list[card_index].name

ocr_agent = ocr_openrouter.CashbackAnalyzer(os.getenv('OPENAI_API_KEY'))

async def ocr_process(screenshot: bytearray):
    return await ocr_agent.analyze_screenshot(screenshot)

async def ocr_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_info = await update.message.photo[-1].get_file()
    downloaded_file = await photo_info.download_as_bytearray()

    recognized_categories = await ocr_process(downloaded_file)
    
    try:
        card_name = assign_categories_to_card(recognized_categories, context)
        await update.message.reply_text(f"Карте {card_name} присвоен список кэшбэков.\n"\
                                    "Для просмотра всех карт и категорий введите /card_list")
    except Exception as e:
         await update.message.reply_text(str(e))        
    finally:
        #await update.message.reply_text(f"Распознанный текст:\n{recognized_categories}")
        return ConversationHandler.END

add_cashback_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add_cashback", add_cashback_1_handler)], #add_cashback_2 - write list of cashback, add_cashback_3 - save list
    states={
        ADD_CASHBACK_2: [CallbackQueryHandler(add_cashback_2_handler)], # обрабатываем нажатие на карту и предлагаем ввести список кэшбэков и процентов
        ADD_CASHBACK_3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cashback_3_handler), MessageHandler(filters.PHOTO, ocr_handler)], # сохраняем список в профиль карты
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
    )

# Редактирование карты
async def edit_card_1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    #restore_state(update, context)
    card_list = get_user_cards(context)

    if card_list == []:
        message = suggest_add_card()
        await update.message.reply_text(message)
        return ConversationHandler.END
    else:
        keyboard = [[InlineKeyboardButton(card.name, callback_data=i)] for i, card in enumerate(card_list)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите карту для редактирования:", reply_markup=reply_markup)
    #context.user_data['state'] = EDIT_CARD
    #store_state(update, context, CHOOSE_CARD_EDIT)
    return EDIT_CARD_2


async def edit_card_2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    context.user_data['selected_card'] = int(query.data)  # Сохраняем индекс выбранной карты из card_list
    await query.answer()

    # Предложим действия
    keyboard = [
        [InlineKeyboardButton("Изменить название карты", callback_data="ecn")], # edit card name
        [InlineKeyboardButton("Удалить карту", callback_data="dc")], # delete card
        [InlineKeyboardButton("Очистить кэшбэки", callback_data="cc")] # clear cashback
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Что вы хотите сделать с картой?", reply_markup=reply_markup) # потенциально нужен await
    return EDIT_CARD_3

async def edit_card_3_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data  # Сохраняем действие с картой
    await query.answer()

    actions = {"ecn": rename_card, "dc": delete_card, "cc": clear_cashbacks}
    return await actions[action](query, context)

# изменяем название карты
async def rename_card(query , context: ContextTypes.DEFAULT_TYPE):
    await query.edit_message_text("Введите новое имя для карты")
    return EDIT_CARD_4

async def edit_card_4_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_list = get_user_cards(context)

    new_card_name = update.message.text
    index = context.user_data['selected_card']
    card_list[index].name = new_card_name

    await update.message.reply_text(f"Новое имя карты - {card_list[index].name}")
    #context.user_data.clear()
    return ConversationHandler.END   

async def delete_card(query , context: ContextTypes.DEFAULT_TYPE) -> int:
    card_list = get_user_cards(context)
    
    del(card_list[context.user_data['selected_card']])
    await query.edit_message_text("Карта удалена")
    #context.user_data.clear()
    return ConversationHandler.END

async def clear_cashbacks(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    card_list = get_user_cards(context)

    index = context.user_data['selected_card']
    card_list[index].cashback_dict.clear()
    await query.edit_message_text(f"Список кэшбэков у карты '{card_list[index].name}' удален")
    #context.user_data.clear()
    return ConversationHandler.END

edit_card_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("edit_card", edit_card_1_handler)], #edit_card_2 - chose action:rename/delete/edit cashback/delete cashback, edit_card_3 - save_new_name/deleted/choose cashback/deleted cashback, edit_card_4 - edit_cashback  
    states={
        EDIT_CARD_2: [CallbackQueryHandler(edit_card_2_handler)], # обрабатывем нажатие на действие
        EDIT_CARD_3: [CallbackQueryHandler(edit_card_3_handler)], # выполняем действие или запрашиваем новое имя карты
        EDIT_CARD_4: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_card_4_handler)], # обновляем имя карты
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)],
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = "Непонятно состояние!!!\n"
    await update.message.reply_text(message)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    message = "Скриншоты я принимаю для добавления категорий внутри ветки /add_cashback.\n"
    await update.message.reply_text(message)

# Главная функция для запуска бота
def main() -> None:
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(os.getenv('TEST_BOT_TOKEN')).build()
    # Обработчики
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("card_list", card_list_handler))

    application.add_handler(add_card_conv_handler)
    application.add_handler(add_cashback_conv_handler)
    application.add_handler(edit_card_conv_handler)
    # Для тестирования OCR
    #application.add_handler(MessageHandler(filters.PHOTO, ocr_handler))

    # Если непонятно состояние и пришёл текст
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT, handle_text))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
