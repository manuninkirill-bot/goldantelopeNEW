from flask import Flask, render_template, jsonify, request, Response
from datetime import datetime, timedelta
import json
import os
import time
import requests
import re
from pathlib import Path

app = Flask(__name__, static_folder='static', static_url_path='/static')

online_users = {}
ONLINE_TIMEOUT = 60
BASE_ONLINE = 287

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def send_telegram_notification(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram notification error: {e}")
        return False

def send_telegram_message(chat_id, message):
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram message error: {e}")
        return False

WELCOME_MESSAGE = """<b>Добро пожаловать в GoldAntelope ASIA!</b>

Крупнейший русскоязычный портал объявлений в Юго-Восточной Азии.

<b>Наши страны:</b>
🇻🇳 Вьетнам (5,800+ объявлений)
🇹🇭 Таиланд (2,400+ объявлений)
🇮🇳 Индия (1,200+ объявлений)
🇮🇩 Индонезия (800+ объявлений)

<b>Категории:</b>
🏠 Недвижимость - аренда и продажа
🍽️ Рестораны и кафе
🧳 Экскурсии и туры
🏍️ Транспорт - байки, авто, яхты
🎮 Развлечения
💱 Обмен валют
🛍️ Барахолка
🏥 Медицина
📰 Новости
💬 Чат сообщества

<b>Контакты:</b>
✈️ Telegram: @radimiralubvi

Подать объявление можно на нашем сайте!
"""

# Данные хранятся в JSON файле по странам
DATA_FILE = "listings_data.json"

def create_empty_data():
    return {
        "restaurants": [],
        "tours": [],
        "transport": [],
        "real_estate": [],
        "money_exchange": [],
        "entertainment": [],
        "marketplace": [],
        "visas": [],
        "news": [],
        "medicine": [],
        "kids": [],
        "chat": []
    }

def load_data(country='vietnam'):
    country_file = f"listings_{country}.json"
    if os.path.exists(country_file):
        with open(country_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            
            # Если данные в файле - список, распределяем по категориям
            result = create_empty_data()
            category_map = {
                'bikes': 'transport',
                'real_estate': 'real_estate',
                'exchange': 'money_exchange',
                'money_exchange': 'money_exchange',
                'food': 'restaurants'
            }
            for item in data:
                if not isinstance(item, dict): continue
                cat = item.get('category', 'chat')
                mapped_cat = category_map.get(cat, cat)
                if mapped_cat in result:
                    result[mapped_cat].append(item)
            return result
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
            if country in all_data:
                return all_data[country]
    return create_empty_data()

def load_all_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'vietnam': create_empty_data(),
        'thailand': create_empty_data(),
        'india': create_empty_data(),
        'indonesia': create_empty_data()
    }

def save_data(country='vietnam', data=None):
    if not data or not isinstance(data, dict):
        return
    
    # Сохраняем в файл страны
    country_file = f"listings_{country}.json"
    try:
        with open(country_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving country file {country_file}: {e}")
    
    # Синхронизируем с общим файлом listings_data.json
    try:
        all_data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        
        all_data[country] = data
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error syncing with listings_data.json: {e}")

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/ping')
def ping():
    user_id = request.args.get('uid', request.remote_addr)
    online_users[user_id] = time.time()
    now = time.time()
    active = sum(1 for t in online_users.values() if now - t < ONLINE_TIMEOUT)
    return jsonify({'online': active})

@app.route('/api/online')
def get_online():
    now = time.time()
    active = sum(1 for t in online_users.values() if now - t < ONLINE_TIMEOUT)
    return jsonify({'online': active})

@app.route('/api/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'ok': True})
        
        message = data.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')
        
        if chat_id and text:
            if text == '/start':
                send_telegram_message(chat_id, WELCOME_MESSAGE)
            elif text == '/help':
                help_text = """<b>Команды бота:</b>

/start - Приветствие и информация о портале
/help - Список команд
/contact - Контакты для связи
/categories - Список категорий"""
                send_telegram_message(chat_id, help_text)
            elif text == '/contact':
                contact_text = """<b>Контакты GoldAntelope ASIA:</b>

✈️ Telegram: @radimiralubvi

Мы всегда рады помочь!"""
                send_telegram_message(chat_id, contact_text)
            elif text == '/categories':
                categories_text = """<b>Категории объявлений:</b>

🏠 Недвижимость
🍽️ Рестораны
🧳 Экскурсии
🏍️ Транспорт
🎮 Развлечения
💱 Обмен валют
🛍️ Барахолка
🏥 Медицина
📰 Новости
💬 Чат"""
                send_telegram_message(chat_id, categories_text)
        
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'ok': True})

@app.route('/api/set-telegram-webhook')
def set_telegram_webhook():
    if not TELEGRAM_BOT_TOKEN:
        return jsonify({'error': 'Bot token not configured'})
    
    domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
    if not domain:
        return jsonify({'error': 'Domain not found'})
    
    webhook_url = f"https://{domain}/api/telegram-webhook"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    
    try:
        response = requests.post(url, data={"url": webhook_url}, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/groups-stats')
def groups_stats():
    """Статистика по группам: охват, онлайн, объявления"""
    country = request.args.get('country', 'thailand')
    data = load_data(country)
    
    # Подсчет объявлений по категориям
    listings_count = {}
    for cat, items in data.items():
        if cat != 'chat':
            listings_count[cat] = len(items)
    
    # Загружаем статистику групп для конкретной страны
    stats_file = f'groups_stats_{country}.json'
    groups = []
    updated = None
    
    # ЗАЩИТА: Не загружаем статистику если файл не существует или пуст для этой страны
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats_data = json.load(f)
            groups = stats_data.get('groups', [])
            updated = stats_data.get('updated')
            
            # Если для этой страны нет данных, НЕ показываем данные от других стран
            if not groups and country != 'thailand':
                # Возвращаем пустой результат вместо fallback на другую страну
                return jsonify({
                    'updated': datetime.now().isoformat(),
                    'categories': {},
                    'groups': [],
                    'total_participants': 0,
                    'total_online': 0,
                    'message': f'Статистика по {country} еще собирается...'
                })
    
    # Агрегируем по категориям
    category_stats = {}
    for g in groups:
        cat = g.get('category', 'Другое')
        if cat not in category_stats:
            category_stats[cat] = {'participants': 0, 'online': 0, 'groups': 0, 'listings': 0}
        category_stats[cat]['participants'] += g.get('participants', 0)
        category_stats[cat]['online'] += g.get('online', 0)
        category_stats[cat]['groups'] += 1
    
    # Добавляем количество объявлений
    cat_key_map = {
        'Недвижимость': 'real_estate',
        'Чат': 'chat',
        'Рестораны': 'restaurants',
        'Для детей': 'entertainment',
        'Барахолка': 'marketplace',
        'Новости': 'news',
        'Визаран': 'visas',
        'Экскурсии': 'tours',
        'Обмен денег': 'money_exchange',
        'Транспорт': 'transport',
        'Медицина': 'medicine'
    }
    
    for cat_name, cat_key in cat_key_map.items():
        if cat_name in category_stats:
            category_stats[cat_name]['listings'] = listings_count.get(cat_key, 0)
    
    return jsonify({
        'updated': updated,
        'categories': category_stats,
        'groups': groups,
        'total_participants': sum(g.get('participants', 0) for g in groups),
        'total_online': sum(g.get('online', 0) for g in groups)
    })

def load_ads_channels(country):
    """Загрузить рекламные каналы"""
    filename = f'ads_channels_{country}.json'
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'channels': []}

def save_ads_channels(country, data):
    """Сохранить рекламные каналы"""
    filename = f'ads_channels_{country}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/api/ads-channels')
def get_ads_channels():
    """Получить список рекламных каналов"""
    country = request.args.get('country', 'vietnam')
    data = load_ads_channels(country)
    return jsonify(data)

@app.route('/api/ads-channels/add', methods=['POST'])
def add_ads_channel():
    """Добавить канал для рекламы"""
    try:
        req = request.json
        country = req.get('country', 'vietnam')
        name = req.get('name', '').strip()
        category = req.get('category', 'chat')
        members = int(req.get('members', 0))
        price = int(req.get('price', 30))
        contact = req.get('contact', '').strip()
        
        if not name or not contact:
            return jsonify({'success': False, 'error': 'Укажите название и контакт'})
        
        data = load_ads_channels(country)
        
        # Проверяем дубликаты
        for ch in data['channels']:
            if ch['name'].lower() == name.lower():
                return jsonify({'success': False, 'error': 'Канал уже добавлен'})
        
        new_channel = {
            'id': f'ad_{int(time.time())}',
            'name': name,
            'category': category,
            'members': members,
            'price': price,
            'contact': contact,
            'added': datetime.now().isoformat()
        }
        
        data['channels'].append(new_channel)
        save_ads_channels(country, data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/status')
def status():
    country = request.args.get('country', 'vietnam')
    data = load_data(country)
    total_items = sum(len(v) for v in data.values())
    total_listings = sum(len(v) for k, v in data.items() if k != 'chat')
    
    # Количество людей на портале по странам
    online_counts = {
        'vietnam': 342,
        'thailand': 287,
        'india': 156,
        'indonesia': 419
    }
    
    return jsonify({
        'parser_status': 'connected',
        'total_items': total_items,
        'total_listings': total_listings,
        'categories': {k: len(v) for k, v in data.items()},
        'last_update': datetime.now().isoformat(),
        'channels_active': 0,
        'country': country,
        'online_count': online_counts.get(country, 100)
    })

@app.route('/api/city-counts/<category>')
def get_city_counts(category):
    country = request.args.get('country', 'vietnam')
    data = load_data(country)
    
    category_aliases = {
        'exchange': 'money_exchange',
        'money_exchange': 'money_exchange',
        'bikes': 'transport',
        'realestate': 'real_estate'
    }
    category = category_aliases.get(category, category)
    
    if category not in data:
        return jsonify({})
    
    listings = data[category]
    listings = [x for x in listings if not x.get('hidden', False)]
    
    city_name_mapping = {
        'Nha Trang': 'Нячанг', 'nha trang': 'Нячанг', 'nhatrang': 'Нячанг',
        'Saigon': 'Хошимин', 'Ho Chi Minh': 'Хошимин', 'saigon': 'Хошимин', 'hcm': 'Хошимин',
        'Da Nang': 'Дананг', 'danang': 'Дананг', 'Danang': 'Дананг',
        'Hanoi': 'Ханой', 'hanoi': 'Ханой', 'Ha Noi': 'Ханой',
        'Phu Quoc': 'Фукуок', 'phuquoc': 'Фукуок', 'Phuquoc': 'Фукуок',
        'Phan Thiet': 'Фантьет', 'phanthiet': 'Фантьет', 'Phanthiet': 'Фантьет',
        'Mui Ne': 'Муйне', 'muine': 'Муйне', 'Muine': 'Муйне',
        'Cam Ranh': 'Камрань', 'camranh': 'Камрань', 'Camranh': 'Камрань',
        'Da Lat': 'Далат', 'dalat': 'Далат', 'Dalat': 'Далат',
        'Hoi An': 'Хойан', 'hoian': 'Хойан', 'Hoian': 'Хойан'
    }
    
    cities = ['Нячанг', 'Хошимин', 'Ханой', 'Фукуок', 'Фантьет', 'Муйне', 'Дананг', 'Камрань', 'Далат', 'Хойан']
    counts = {city: 0 for city in cities}
    
    for item in listings:
        item_city = item.get('city', '') or item.get('location', '')
        normalized = city_name_mapping.get(item_city, item_city)
        if normalized in counts:
            counts[normalized] += 1
        else:
            for search_city in cities:
                search_text = f"{item.get('title', '')} {item.get('description', '')} {item_city}".lower()
                if search_city.lower() in search_text:
                    counts[search_city] += 1
                    break
    
    return jsonify(counts)

@app.route('/api/listings/<category>')
def get_listings(category):
    country = request.args.get('country', 'vietnam')
    data = load_data(country)
    
    category_aliases = {
        'exchange': 'money_exchange',
        'money_exchange': 'money_exchange',
        'bikes': 'transport',
        'realestate': 'real_estate',
        'admin': 'restaurants',
        'settings': 'restaurants',
        'stats': 'restaurants'
    }
    category = category_aliases.get(category, category)
    
    if category not in data:
        return jsonify([])
    
    listings = data[category]
    
    # Фильтры
    filters = request.args
    
    # Фильтруем скрытые объявления (если не запрошено show_hidden=1)
    show_hidden = request.args.get('show_hidden', '0') == '1'
    if show_hidden:
        filtered = listings  # Админ видит все
    else:
        filtered = [x for x in listings if not x.get('hidden', False)]
    
    # Маппинг русских названий городов на английские
    city_name_mapping = {
        'Нячанг': 'Nha Trang',
        'Хошимин': 'Saigon',
        'Сайгон': 'Saigon',
        'Saigon': 'Saigon',
        'Ho Chi Minh': 'Saigon',
        'Дананг': 'Da Nang',
        'Ханой': 'Hanoi',
        'Фукуок': 'Phu Quoc',
        'Фантьет': 'Phan Thiet',
        'Муйне': 'Mui Ne',
        'Камрань': 'Cam Ranh',
        'Далат': 'Da Lat',
        'Хойан': 'Hoi An'
    }
    
    # Универсальный фильтр по городу для категорий, где он есть (restaurants, tours, entertainment)
    if category in ['restaurants', 'tours', 'entertainment']:
        if 'city' in filters and filters['city']:
            city_filter = filters['city']
            # Поиск по русскому названию напрямую (данные теперь на русском)
            targets = [city_filter.lower()]
            # Также добавляем английские варианты для совместимости
            city_en = city_name_mapping.get(city_filter, city_filter)
            targets.append(city_en.lower())
            targets.append(city_en.replace(' ', '').lower())
            
            # Особые случаи для Сайгона/Хошимина
            if city_filter.lower() in ['хошимин', 'сайгон'] or city_en.lower() == 'saigon':
                targets.extend(['saigon', 'ho chi minh', 'hochiminh', 'хошимин', 'сайгон'])
            
            filtered = [x for x in filtered if str(x.get('city', '')).lower() in targets or str(x.get('location', '')).lower() in targets]
            print(f"DEBUG: Category {category}, City Filter {city_filter}, Targets {targets}, Found {len(filtered)} items")
    
    # Фильтр по типу для категории "kids" (Для детей)
    if category == 'kids':
        if 'kids_type' in filters and filters['kids_type']:
            kids_type = filters['kids_type']
            # Сначала проверяем поле kids_type
            filtered_by_field = [x for x in filtered if x.get('kids_type') == kids_type]
            
            # Если нет результатов по полю, ищем по ключевым словам
            if not filtered_by_field:
                type_keywords = {
                    'events': ['мероприят', 'праздник', 'игр', 'развлечен', 'день рожден', 'аниматор', 'event', 'party', 'утренник'],
                    'nannies': ['нян', 'репетитор', 'кружок', 'секци', 'занят', 'урок', 'babysitter', 'tutor', 'обучен'],
                    'schools': ['садик', 'школ', 'лицей', 'гимназ', 'образован', 'детский сад', 'kindergarten', 'school', 'дошкольн']
                }
                keywords = type_keywords.get(kids_type, [])
                if keywords:
                    filtered = [x for x in filtered if any(kw in (x.get('description', '') + ' ' + x.get('title', '')).lower() for kw in keywords)]
            else:
                filtered = filtered_by_field
        
        # Фильтр по городу для kids
        if 'city' in filters and filters['city']:
            city_filter = filters['city'].lower()
            city_mapping = {
                'nha trang': ['nha trang', 'nhatrang', 'нячанг'],
                'da nang': ['da nang', 'danang', 'дананг'],
                'phu quoc': ['phu quoc', 'phuquoc', 'фукуок'],
                'ho chi minh': ['ho chi minh', 'hochiminh', 'hcm', 'хошимин', 'сайгон']
            }
            targets = city_mapping.get(city_filter, [city_filter])
            filtered = [x for x in filtered if any(t in str(x.get('city', '')).lower() for t in targets)]
        
        # Фильтр по возрасту для kids
        if 'max_age' in filters and filters['max_age']:
            try:
                max_age = int(filters['max_age'])
                def check_age(item):
                    age_str = str(item.get('age', ''))
                    # Извлекаем числа из строки возраста
                    import re
                    numbers = re.findall(r'\d+', age_str)
                    if numbers:
                        # Берём минимальный возраст из диапазона
                        min_item_age = min(int(n) for n in numbers)
                        return min_item_age <= max_age
                    return True  # Если возраст не указан, показываем
                filtered = [x for x in filtered if check_age(x)]
            except ValueError:
                pass
    
    if category == 'transport':
        # Фильтр по городу для transport
        if 'city' in filters and filters['city']:
            city_filter = filters['city'].lower()
            city_mapping = {
                'nha trang': ['nha trang', 'nhatrang', 'нячанг'],
                'da nang': ['da nang', 'danang', 'дананг'],
                'phu quoc': ['phu quoc', 'phuquoc', 'фукуок'],
                'ho chi minh': ['ho chi minh', 'hochiminh', 'hcm', 'хошимин', 'сайгон']
            }
            targets = city_mapping.get(city_filter, [city_filter])
            filtered = [x for x in filtered if any(t in str(x.get('city', '')).lower() or t in str(x.get('location', '')).lower() or t in str(x.get('description', '')).lower() for t in targets)]
        
        # Фильтр по типу (sale, rent)
        if 'type' in filters and filters['type']:
            type_filter = filters['type'].lower()
            if type_filter == 'sale':
                keywords = ['продаж', 'куплю', 'продам', 'цена', '$', '₫', 'доллар']
                filtered = [x for x in filtered if any(kw in x.get('description', '').lower() for kw in keywords)]
            elif type_filter == 'rent':
                keywords = ['аренд', 'сдам', 'сдаю', 'наём', 'прокат', 'почасово']
                filtered = [x for x in filtered if any(kw in x.get('description', '').lower() for kw in keywords)]
        
        if 'model' in filters and filters['model']:
            filtered = [x for x in filtered if filters['model'].lower() in (x.get('model') or '').lower()]
        if 'year' in filters and filters['year']:
            filtered = [x for x in filtered if str(x.get('year', '')) == filters['year']]
        if 'price_min' in filters and 'price_max' in filters and filters['price_min'] and filters['price_max']:
            try:
                min_p, max_p = float(filters['price_min']), float(filters['price_max'])
                filtered = [x for x in filtered if min_p <= x.get('price', 0) <= max_p]
            except:
                pass
    
    elif category == 'real_estate':
        if 'realestate_city' in filters and filters['realestate_city']:
            city_filter = filters['realestate_city']
            filtered = [x for x in filtered if x.get('city', 'nhatrang') == city_filter]
        
        if 'listing_type' in filters and filters['listing_type']:
            type_filter = filters['listing_type']
            filtered = [x for x in filtered if type_filter in (x.get('listing_type') or '')]
        
        def get_price_int(item):
            # Сначала пробуем поле price
            price = item.get('price')
            if price is not None:
                if isinstance(price, (int, float)) and price > 0:
                    return int(price)
                try:
                    price_str = str(price).lower()
                    multiplier = 1
                    if 'млн' in price_str or 'mln' in price_str or 'миллион' in price_str:
                        multiplier = 1000000
                    price_str = price_str.replace(',', '.')
                    price_str = re.sub(r'[^\d.]', '', price_str)
                    parts = price_str.split('.')
                    if len(parts) > 2:
                        price_str = parts[0] + '.' + ''.join(parts[1:])
                    if price_str:
                        val = int(float(price_str) * multiplier)
                        if val > 0:
                            return val
                except:
                    pass
            
            # Если поле price пустое или 0, извлекаем из описания
            desc = (item.get('description') or '').lower()
            
            # Ищем паттерны: "7,5 миллион", "7.5 млн", "Цена: 7 500 000"
            import re
            patterns = [
                r'(\d+[,.]?\d*)\s*(?:миллион|млн|mln)',  # 7,5 миллион
                r'цена[:\s]*(\d[\d\s]*)\s*(?:vnd|донг|₫)?',  # Цена: 7 500 000
                r'(\d[\d\s]{2,})\s*(?:vnd|донг|₫)',  # 7 500 000 VND
            ]
            
            for pattern in patterns:
                match = re.search(pattern, desc)
                if match:
                    price_str = match.group(1).replace(' ', '').replace(',', '.')
                    try:
                        val = float(price_str)
                        # Если число маленькое и паттерн с млн/миллион
                        if val < 1000 and 'млн' in pattern or 'миллион' in pattern:
                            val = val * 1000000
                        elif val < 100:
                            val = val * 1000000
                        return int(val)
                    except:
                        pass
            
            return 0

        # Price filtering
        if 'price_max' in filters and filters['price_max']:
            try:
                max_p = int(filters['price_max'])
                filtered = [x for x in filtered if 0 < get_price_int(x) <= max_p]
            except:
                pass
        
        sort_type = filters.get('sort')
        if sort_type == 'price_desc':
            filtered.sort(key=get_price_int, reverse=True)
        elif sort_type == 'price_asc':
            filtered.sort(key=get_price_int)
        else:
            filtered.sort(key=lambda x: x.get('date', x.get('added_at', '1970-01-01')) or '1970-01-01', reverse=True)
        
        # Обновляем URL для фото из Telegram
        for item in filtered:
            if item.get('telegram_file_id'):
                fresh_url = get_telegram_photo_url(item['telegram_file_id'])
                if fresh_url:
                    item['image_url'] = fresh_url
        return jsonify(filtered)
    
    # Сортировка по дате - новые сверху
    filtered.sort(key=lambda x: x.get('date', x.get('added_at', '1970-01-01')) or '1970-01-01', reverse=True)
    
    # Обновляем URL для фото из Telegram (генерируем свежие ссылки)
    for item in filtered:
        if item.get('telegram_file_id'):
            fresh_url = get_telegram_photo_url(item['telegram_file_id'])
            if fresh_url:
                item['image_url'] = fresh_url
    
    return jsonify(filtered)

@app.route('/api/add-listing', methods=['POST'])
def add_listing():
    country = request.json.get('country', 'vietnam')
    data = load_data(country)
    listing = request.json
    
    category = listing.get('category')
    if category and category in data:
        listing['added_at'] = datetime.now().isoformat()
        data[category].append(listing)
        save_data(country, data)
        return jsonify({'success': True, 'message': 'Объявление добавлено'})
    
    return jsonify({'error': 'Invalid category'}), 400

import shutil
from werkzeug.utils import secure_filename
import requests

BUNNY_STORAGE_ZONE = os.environ.get('BUNNY_CDN_STORAGE_ZONE', 'storage.bunnycdn.com')
BUNNY_STORAGE_NAME = os.environ.get('BUNNY_CDN_STORAGE_NAME', 'goldantelope')
BUNNY_API_KEY = os.environ.get('BUNNY_CDN_API_KEY', 'c88e0b0b-d63c-4a45-8b3d1819830a-c07a-4ddb')

def upload_to_bunny(local_path, filename):
    url = f"https://{BUNNY_STORAGE_ZONE}/{BUNNY_STORAGE_NAME}/{filename}"
    headers = {
        "AccessKey": BUNNY_API_KEY,
        "Content-Type": "application/octet-stream",
    }
    try:
        with open(local_path, "rb") as f:
            response = requests.put(url, data=f, headers=headers)
            return response.status_code == 201
    except Exception as e:
        print(f"BunnyCDN Upload Error: {e}")
        return False

BANNER_CONFIG_FILE = "banner_config.json"
UPLOAD_FOLDER = 'static/images/banners'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def load_banner_config():
    if os.path.exists(BANNER_CONFIG_FILE):
        with open(BANNER_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'vietnam': ['/static/images/banners/vietnam1.jpg', '/static/images/banners/vietnam2.jpg', '/static/images/banners/vietnam3.jpg', '/static/images/banners/vietnam4.jpg'],
        'thailand': ['/static/images/banner_thailand.jpg'],
        'india': ['/static/images/banner_india.jpg'],
        'indonesia': ['/static/images/banner_indonesia.jpg']
    }

def save_banner_config(config):
    with open(BANNER_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

@app.route('/api/banners')
def get_banners():
    return jsonify(load_banner_config())

@app.route('/api/admin/upload-banner', methods=['POST'])
def admin_upload_banner():
    password = request.form.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.form.get('country', 'vietnam')
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(f"{country}_{int(time.time())}_{file.filename}")
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Загружаем в BunnyCDN
        upload_to_bunny(file_path, filename)
        
        url = f'/static/images/banners/{filename}'
        config = load_banner_config()
        if country not in config:
            config[country] = []
        config[country].append(url)
        save_banner_config(config)
        
        return jsonify({'success': True, 'url': url})

@app.route('/api/admin/delete-banner', methods=['POST'])
def admin_delete_banner():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country')
    url = request.json.get('url')
    
    config = load_banner_config()
    if country in config and url in config[country]:
        config[country].remove(url)
        save_banner_config(config)
        # Мы не удаляем файл физически для безопасности, просто убираем из конфига
        return jsonify({'success': True})
    return jsonify({'error': 'Banner not found'}), 404

@app.route('/api/admin/reorder-banners', methods=['POST'])
def admin_reorder_banners():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country')
    urls = request.json.get('urls')
    
    config = load_banner_config()
    if country in config:
        config[country] = urls
        save_banner_config(config)
        return jsonify({'success': True})
    return jsonify({'error': 'Country not found'}), 404

@app.route('/api/admin/auth', methods=['POST'])
def admin_auth():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password == admin_key:
        return jsonify({'success': True, 'authenticated': True})
    return jsonify({'success': False, 'error': 'Invalid password'}), 401

@app.route('/api/admin/delete-listing', methods=['POST'])
def admin_delete():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category')
    listing_id = request.json.get('listing_id')
    
    data = load_data(country)
    
    if category in data:
        data[category] = [x for x in data[category] if x.get('id') != listing_id]
        save_data(country, data)
        return jsonify({'success': True, 'message': f'Объявление {listing_id} удалено'})
    
    return jsonify({'error': 'Category not found'}), 404

@app.route('/api/admin/move-listing', methods=['POST'])
def admin_move():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    from_category = request.json.get('from_category')
    to_category = request.json.get('to_category')
    listing_id = request.json.get('listing_id')
    
    data = load_data(country)
    
    if from_category not in data or to_category not in data:
        return jsonify({'error': 'Invalid category'}), 404
    
    # Найти объявление
    listing = None
    if from_category in data:
        for i, item in enumerate(data[from_category]):
            if item.get('id') == listing_id:
                listing = data[from_category].pop(i)
                break
    
    if not listing:
        return jsonify({'success': False, 'error': 'Listing not found'}), 404
    
    # Обновить категорию и переместить
    listing['category'] = to_category
    if to_category not in data:
        data[to_category] = []
    data[to_category].insert(0, listing)
    save_data(country, data)
    
    return jsonify({'success': True, 'message': f'Объявление перемещено в {to_category}'})

@app.route('/api/admin/toggle-visibility', methods=['POST'])
def admin_toggle_visibility():
    """Скрыть/показать объявление"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category')
    listing_id = request.json.get('listing_id')
    
    data = load_data(country)
    
    if category not in data:
        return jsonify({'error': 'Category not found'}), 404
    
    for item in data[category]:
        if item.get('id') == listing_id:
            current = item.get('hidden', False)
            item['hidden'] = not current
            save_data(country, data)
            status = 'скрыто' if item['hidden'] else 'видимо'
            return jsonify({'success': True, 'hidden': item['hidden'], 'message': f'Объявление {status}'})
    
    return jsonify({'error': 'Listing not found'}), 404

@app.route('/api/admin/bulk-hide', methods=['POST'])
def admin_bulk_hide():
    """Массовое скрытие объявлений по контакту"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category')
    contact_name = request.json.get('contact_name')
    hide = request.json.get('hide', True)
    
    data = load_data(country)
    count = 0
    
    if category and category in data:
        categories = [category]
    else:
        categories = data.keys()
    
    for cat in categories:
        if cat in data:
            for item in data[cat]:
                cn = (item.get('contact_name') or item.get('contact') or '').lower()
                if contact_name.lower() in cn:
                    item['hidden'] = hide
                    count += 1
    
    save_data(country, data)
    action = 'скрыто' if hide else 'показано'
    return jsonify({'success': True, 'count': count, 'message': f'{count} объявлений {action}'})

@app.route('/api/admin/edit-listing', methods=['POST'])
def admin_edit():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category')
    listing_id = request.json.get('listing_id')
    updates = request.json.get('updates', {})
    
    data = load_data(country)
    
    if category not in data:
        return jsonify({'error': 'Category not found'}), 404
    
    for item in data[category]:
        if item.get('id') == listing_id:
            if 'title' in updates:
                item['title'] = updates['title']
            if 'description' in updates:
                item['description'] = updates['description']
            if 'price' in updates:
                try:
                    item['price'] = int(updates['price']) if updates['price'] else 0
                except:
                    item['price'] = 0
            if 'rooms' in updates:
                item['rooms'] = updates['rooms'] if updates['rooms'] else None
            if 'area' in updates:
                try:
                    item['area'] = float(updates['area']) if updates['area'] else None
                except:
                    item['area'] = None
            if 'date' in updates:
                item['date'] = updates['date'] if updates['date'] else None
            if 'whatsapp' in updates:
                item['whatsapp'] = updates['whatsapp'] if updates['whatsapp'] else None
            if 'telegram' in updates:
                item['telegram'] = updates['telegram'] if updates['telegram'] else None
            if 'contact_name' in updates:
                item['contact_name'] = updates['contact_name'] if updates['contact_name'] else None
            if 'listing_type' in updates:
                item['listing_type'] = updates['listing_type'] if updates['listing_type'] else None
            if 'city' in updates:
                item['city'] = updates['city'] if updates['city'] else None
            if 'google_maps' in updates:
                item['google_maps'] = updates['google_maps'] if updates['google_maps'] else None
            if 'google_rating' in updates:
                item['google_rating'] = updates['google_rating'] if updates['google_rating'] else None
            if 'kitchen' in updates:
                item['kitchen'] = updates['kitchen'] if updates['kitchen'] else None
            if 'restaurant_type' in updates:
                item['restaurant_type'] = updates['restaurant_type'] if updates['restaurant_type'] else None
            if 'price_category' in updates:
                item['price_category'] = updates['price_category'] if updates['price_category'] else None
            
            save_data(country, data)
            return jsonify({'success': True, 'message': 'Объявление обновлено'})
    
    return jsonify({'error': 'Listing not found'}), 404

@app.route('/api/admin/get-listing', methods=['POST'])
def admin_get_listing():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category')
    listing_id = request.json.get('listing_id')
    
    data = load_data(country)
    
    if category not in data:
        return jsonify({'error': 'Category not found'}), 404
    
    for item in data[category]:
        if item.get('id') == listing_id:
            return jsonify(item)
    
    return jsonify({'error': 'Listing not found'}), 404

def load_pending_listings(country='vietnam'):
    pending_file = f"pending_{country}.json"
    if os.path.exists(pending_file):
        with open(pending_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_pending_listings(country, listings):
    pending_file = f"pending_{country}.json"
    with open(pending_file, 'w', encoding='utf-8') as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)

@app.route('/api/submit-listing', methods=['POST'])
def submit_listing():
    try:
        captcha_answer = request.form.get('captcha_answer', '')
        captcha_token = request.form.get('captcha_token', '')
        
        expected = captcha_storage.get(captcha_token)
        if not expected or captcha_answer != expected:
            return jsonify({'error': 'Неверная капча'}), 400
        
        if captcha_token in captcha_storage:
            del captcha_storage[captcha_token]
        
        country = request.form.get('country', 'vietnam')
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        price = request.form.get('price', '')
        rooms = request.form.get('rooms', '')
        area = request.form.get('area', '')
        location = request.form.get('location', '')
        city = request.form.get('city', '')
        contact_name = request.form.get('contact_name', '')
        whatsapp = request.form.get('whatsapp', '')
        telegram = request.form.get('telegram', '')
        listing_type = request.form.get('listing_type', '')
        
        if not title or not description:
            return jsonify({'error': 'Заполните название и описание'}), 400
        
        images = []
        for i in range(4):
            file = request.files.get(f'photo_{i}')
            if file and file.filename:
                if file.content_length and file.content_length > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                import base64
                file_data = file.read()
                if len(file_data) > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                data_url = f"data:image/{ext};base64,{base64.b64encode(file_data).decode()}"
                images.append(data_url)
        
        listing_id = f"pending_{country}_{int(time.time())}_{len(load_pending_listings(country))}"
        
        new_listing = {
            'id': listing_id,
            'title': title,
            'description': description,
            'price': int(price) if price.isdigit() else 0,
            'rooms': rooms if rooms else None,
            'area': float(area) if area else None,
            'location': location if location else None,
            'city': city if city else None,
            'contact_name': contact_name,
            'whatsapp': whatsapp,
            'telegram': telegram,
            'listing_type': listing_type,
            'image_url': images[0] if images else None,
            'all_images': images if len(images) > 1 else None,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        pending = load_pending_listings(country)
        pending.append(new_listing)
        save_pending_listings(country, pending)
        
        send_telegram_notification(f"<b>Новое объявление (Недвижимость)</b>\n\n<b>{title}</b>\n{description[:200]}...\n\nЦена: {price}\n\n✈️ Написать в Telegram: @radimiralubvi")
        
        return jsonify({'success': True, 'message': 'Объявление отправлено на модерацию'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-restaurant', methods=['POST'])
def submit_restaurant():
    try:
        captcha_answer = request.form.get('captcha_answer', '')
        captcha_token = request.form.get('captcha_token', '')
        
        expected = captcha_storage.get(captcha_token)
        if not expected or captcha_answer != expected:
            return jsonify({'error': 'Неверная капча'}), 400
        
        if captcha_token in captcha_storage:
            del captcha_storage[captcha_token]
        
        country = request.form.get('country', 'vietnam')
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        kitchen = request.form.get('kitchen', '')
        location = request.form.get('location', '')
        city = request.form.get('city', '')
        google_maps = request.form.get('google_maps', '')
        contact_name = request.form.get('contact_name', '')
        whatsapp = request.form.get('whatsapp', '')
        telegram = request.form.get('telegram', '')
        price_category = request.form.get('price_category', 'normal')
        restaurant_type = request.form.get('restaurant_type', 'ресторан')
        
        if not title or not description:
            return jsonify({'error': 'Заполните название и описание'}), 400
        
        images = []
        for i in range(4):
            file = request.files.get(f'photo_{i}')
            if file and file.filename:
                import base64
                file_data = file.read()
                if len(file_data) > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                data_url = f"data:image/{ext};base64,{base64.b64encode(file_data).decode()}"
                images.append(data_url)
        
        listing_id = f"pending_restaurant_{country}_{int(time.time())}_{len(load_pending_listings(country))}"
        
        new_listing = {
            'id': listing_id,
            'title': title,
            'description': description,
            'kitchen': kitchen if kitchen else None,
            'location': location if location else None,
            'city': city if city else None,
            'google_maps': google_maps if google_maps else None,
            'restaurant_type': restaurant_type if restaurant_type else 'ресторан',
            'contact_name': contact_name,
            'whatsapp': whatsapp,
            'telegram': telegram,
            'price_category': price_category,
            'category': 'restaurants',
            'image_url': images[0] if images else None,
            'all_images': images if len(images) > 1 else None,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        pending = load_pending_listings(country)
        pending.append(new_listing)
        save_pending_listings(country, pending)
        
        send_telegram_notification(f"<b>Новый ресторан</b>\n\n<b>{title}</b>\n{description[:200]}...\n\nКухня: {kitchen}\n\n✈️ Написать в Telegram: @radimiralubvi")
        
        return jsonify({'success': True, 'message': 'Ресторан отправлен на модерацию'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-entertainment', methods=['POST'])
def submit_entertainment():
    try:
        captcha_answer = request.form.get('captcha_answer', '')
        captcha_token = request.form.get('captcha_token', '')
        
        expected = captcha_storage.get(captcha_token)
        if not expected or captcha_answer != expected:
            return jsonify({'error': 'Неверная капча'}), 400
        
        if captcha_token in captcha_storage:
            del captcha_storage[captcha_token]
        
        country = request.form.get('country', 'vietnam')
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        feature = request.form.get('feature', '')
        location = request.form.get('location', '')
        city = request.form.get('city', '')
        contact_name = request.form.get('contact_name', '')
        whatsapp = request.form.get('whatsapp', '')
        telegram = request.form.get('telegram', '')
        capacity = request.form.get('capacity', '50')
        
        if not title or not description:
            return jsonify({'error': 'Заполните название и описание'}), 400
        
        images = []
        for i in range(4):
            file = request.files.get(f'photo_{i}')
            if file and file.filename:
                import base64
                file_data = file.read()
                if len(file_data) > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                data_url = f"data:image/{ext};base64,{base64.b64encode(file_data).decode()}"
                images.append(data_url)
        
        listing_id = f"pending_entertainment_{country}_{int(time.time())}_{len(load_pending_listings(country))}"
        
        new_listing = {
            'id': listing_id,
            'title': title,
            'description': description,
            'feature': feature if feature else None,
            'location': location if location else None,
            'city': city if city else None,
            'contact_name': contact_name,
            'whatsapp': whatsapp,
            'telegram': telegram,
            'capacity': capacity,
            'category': 'entertainment',
            'image_url': images[0] if images else None,
            'all_images': images if len(images) > 1 else None,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        pending = load_pending_listings(country)
        pending.append(new_listing)
        save_pending_listings(country, pending)
        
        send_telegram_notification(f"<b>Новое развлечение</b>\n\n<b>{title}</b>\n{description[:200]}...\n\nФишка: {feature}\n\n✈️ Написать в Telegram: @radimiralubvi")
        
        return jsonify({'success': True, 'message': 'Развлечение отправлено на модерацию'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-tour', methods=['POST'])
def submit_tour():
    try:
        captcha_answer = request.form.get('captcha_answer', '')
        captcha_token = request.form.get('captcha_token', '')
        
        expected = captcha_storage.get(captcha_token)
        if not expected or captcha_answer != expected:
            return jsonify({'error': 'Неверная капча'}), 400
        
        if captcha_token in captcha_storage:
            del captcha_storage[captcha_token]
        
        country = request.form.get('country', 'vietnam')
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        days = request.form.get('days', '1')
        price = request.form.get('price', '')
        location = request.form.get('location', '')
        city = request.form.get('city', '')
        contact_name = request.form.get('contact_name', '')
        whatsapp = request.form.get('whatsapp', '')
        telegram = request.form.get('telegram', '')
        group_size = request.form.get('group_size', '5')
        
        if not title or not description:
            return jsonify({'error': 'Заполните название и описание'}), 400
        
        images = []
        for i in range(4):
            file = request.files.get(f'photo_{i}')
            if file and file.filename:
                import base64
                file_data = file.read()
                if len(file_data) > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                data_url = f"data:image/{ext};base64,{base64.b64encode(file_data).decode()}"
                images.append(data_url)
        
        listing_id = f"pending_tour_{country}_{int(time.time())}_{len(load_pending_listings(country))}"
        
        new_listing = {
            'id': listing_id,
            'title': title,
            'description': description,
            'days': days,
            'price': int(price) if price.isdigit() else 0,
            'location': location if location else None,
            'city': city if city else None,
            'contact_name': contact_name,
            'whatsapp': whatsapp,
            'telegram': telegram,
            'group_size': group_size,
            'category': 'tours',
            'image_url': images[0] if images else None,
            'all_images': images if len(images) > 1 else None,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        pending = load_pending_listings(country)
        pending.append(new_listing)
        save_pending_listings(country, pending)
        
        send_telegram_notification(f"<b>Новая экскурсия</b>\n\n<b>{title}</b>\n{description[:200]}...\n\nДней: {days}, Цена: ${price}\n\n✈️ Написать в Telegram: @radimiralubvi")
        
        return jsonify({'success': True, 'message': 'Экскурсия отправлена на модерацию'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-transport', methods=['POST'])
def submit_transport():
    try:
        captcha_answer = request.form.get('captcha_answer', '')
        captcha_token = request.form.get('captcha_token', '')
        
        expected = captcha_storage.get(captcha_token)
        if not expected or captcha_answer != expected:
            return jsonify({'error': 'Неверная капча'}), 400
        
        if captcha_token in captcha_storage:
            del captcha_storage[captcha_token]
        
        country = request.form.get('country', 'vietnam')
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        engine = request.form.get('engine', '')
        year = request.form.get('year', '')
        price = request.form.get('price', '')
        transport_type = request.form.get('transport_type', 'bikes')
        location = request.form.get('location', '')
        city = request.form.get('city', '')
        contact_name = request.form.get('contact_name', '')
        whatsapp = request.form.get('whatsapp', '')
        telegram = request.form.get('telegram', '')
        
        if not title or not description:
            return jsonify({'error': 'Заполните название и описание'}), 400
        
        images = []
        for i in range(4):
            file = request.files.get(f'photo_{i}')
            if file and file.filename:
                import base64
                file_data = file.read()
                if len(file_data) > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                data_url = f"data:image/{ext};base64,{base64.b64encode(file_data).decode()}"
                images.append(data_url)
        
        listing_id = f"pending_transport_{country}_{int(time.time())}_{len(load_pending_listings(country))}"
        
        new_listing = {
            'id': listing_id,
            'title': title,
            'description': description,
            'engine': engine,
            'year': int(year) if year.isdigit() else None,
            'price': int(price) if price.isdigit() else 0,
            'transport_type': transport_type,
            'location': location if location else None,
            'city': city if city else None,
            'contact_name': contact_name,
            'whatsapp': whatsapp,
            'telegram': telegram,
            'category': 'transport',
            'image_url': images[0] if images else None,
            'all_images': images if len(images) > 1 else None,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        pending = load_pending_listings(country)
        pending.append(new_listing)
        save_pending_listings(country, pending)
        
        send_telegram_notification(f"<b>Новый транспорт</b>\n\n<b>{title}</b>\n{description[:200]}...\n\nДвигатель: {engine}cc, Год: {year}, Цена: ${price}\n\n✈️ Написать в Telegram: @radimiralubvi")
        
        return jsonify({'success': True, 'message': 'Транспорт отправлен на модерацию'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-kids', methods=['POST'])
def submit_kids():
    try:
        captcha_answer = request.form.get('captcha_answer', '')
        captcha_token = request.form.get('captcha_token', '')
        
        expected = captcha_storage.get(captcha_token)
        if not expected or captcha_answer != expected:
            return jsonify({'error': 'Неверная капча'}), 400
        
        if captcha_token in captcha_storage:
            del captcha_storage[captcha_token]
        
        country = request.form.get('country', 'vietnam')
        title = request.form.get('title', '')
        kids_type = request.form.get('kids_type', 'schools')
        description = request.form.get('description', '')
        city = request.form.get('city', '')
        age = request.form.get('age', '')
        location = request.form.get('location', '')
        google_maps = request.form.get('google_maps', '')
        contact_name = request.form.get('contact_name', '')
        whatsapp = request.form.get('whatsapp', '')
        telegram = request.form.get('telegram', '')
        
        if not title or not description:
            return jsonify({'error': 'Заполните название и описание'}), 400
        
        if not city or not age:
            return jsonify({'error': 'Заполните город и возраст'}), 400
        
        images = []
        for i in range(4):
            file = request.files.get(f'photo_{i}')
            if file and file.filename:
                import base64
                file_data = file.read()
                if len(file_data) > 1024 * 1024:
                    return jsonify({'error': f'Фото {i+1} превышает 1 МБ'}), 400
                
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                data_url = f"data:image/{ext};base64,{base64.b64encode(file_data).decode()}"
                images.append(data_url)
        
        listing_id = f"pending_kids_{country}_{int(time.time())}_{len(load_pending_listings(country))}"
        
        new_listing = {
            'id': listing_id,
            'title': title,
            'kids_type': kids_type,
            'description': description,
            'city': city,
            'age': age,
            'location': location if location else None,
            'google_maps': google_maps if google_maps else None,
            'contact_name': contact_name,
            'whatsapp': whatsapp,
            'telegram': telegram,
            'category': 'kids',
            'image_url': images[0] if images else None,
            'all_images': images if len(images) > 1 else None,
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        pending = load_pending_listings(country)
        pending.append(new_listing)
        save_pending_listings(country, pending)
        
        kids_type_labels = {'schools': 'Садики и школы', 'events': 'Мероприятия', 'nannies': 'Няни и кружки'}
        send_telegram_notification(f"<b>Новое объявление для детей</b>\n\n<b>{title}</b>\nТип: {kids_type_labels.get(kids_type, kids_type)}\nГород: {city}\nВозраст: {age}\n\n{description[:200]}...\n\n✈️ @radimiralubvi")
        
        return jsonify({'success': True, 'message': 'Объявление отправлено на модерацию'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/pending', methods=['POST'])
def admin_get_pending():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    pending = load_pending_listings(country)
    return jsonify(pending)

@app.route('/api/admin/moderate', methods=['POST'])
def admin_moderate():
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    listing_id = request.json.get('listing_id')
    action = request.json.get('action')
    
    pending = load_pending_listings(country)
    listing = None
    
    for i, item in enumerate(pending):
        if item.get('id') == listing_id:
            listing = pending.pop(i)
            break
    
    if not listing:
        return jsonify({'error': 'Listing not found'}), 404
    
    save_pending_listings(country, pending)
    
    if action == 'approve':
        # Определяем категорию из объявления
        category = listing.get('category', 'real_estate')
        listing['id'] = f"{country}_{category}_{int(time.time())}"
        listing['status'] = 'approved'
        
        # Отправляем фото в Telegram канал и получаем URL
        print(f"MODERATION: Checking image_url for listing {listing.get('id')}")
        print(f"MODERATION: image_url exists: {bool(listing.get('image_url'))}")
        if listing.get('image_url'):
            try:
                import base64
                image_url = listing['image_url']
                image_data = None
                print(f"MODERATION: image_url type: {image_url[:50] if image_url else 'None'}...")
                
                # Если это base64 data URL
                if image_url.startswith('data:'):
                    print("MODERATION: Decoding base64 image...")
                    header, b64_data = image_url.split(',', 1)
                    image_data = base64.b64decode(b64_data)
                    print(f"MODERATION: Decoded {len(image_data)} bytes")
                # Если это локальный файл
                elif image_url.startswith('/static/') or image_url.startswith('static/'):
                    file_path = image_url.lstrip('/')
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            image_data = f.read()
                # Если это внешний URL
                elif image_url.startswith('http'):
                    try:
                        resp = requests.get(image_url, timeout=30)
                        if resp.status_code == 200:
                            image_data = resp.content
                    except:
                        pass
                
                if image_data:
                    # Отправляем в Telegram канал и получаем file_id
                    caption = f"📋 {listing.get('title', 'Объявление')}\n\n{listing.get('description', '')[:500]}"
                    file_id = send_photo_to_channel(image_data, caption)
                    
                    if file_id:
                        listing['telegram_file_id'] = file_id
                        listing['telegram_photo'] = True
                        # Получаем актуальный URL для первоначального отображения
                        fresh_url = get_telegram_photo_url(file_id)
                        if fresh_url:
                            listing['image_url'] = fresh_url
            except Exception as e:
                print(f"Error uploading photo to Telegram: {e}")
        
        data = load_data(country)
        if category not in data:
            data[category] = []
        data[category].insert(0, listing)
        save_data(country, data)
        return jsonify({'success': True, 'message': f'Объявление одобрено и добавлено в {category}'})
    else:
        return jsonify({'success': True, 'message': 'Объявление отклонено'})

captcha_storage = {}

@app.route('/api/captcha')
def get_captcha():
    import random
    import uuid
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    token = str(uuid.uuid4())[:8]
    captcha_storage[token] = str(a + b)
    if len(captcha_storage) > 1000:
        keys = list(captcha_storage.keys())[:500]
        for k in keys:
            del captcha_storage[k]
    return jsonify({'question': f'{a} + {b} = ?', 'token': token})

@app.route('/api/parser-config', methods=['GET', 'POST'])
def parser_config():
    country = request.args.get('country', 'vietnam')
    config_file = f'parser_config_{country}.json'
    
    if request.method == 'POST':
        config = request.json
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True})
    
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    
    return jsonify({
        'channels': [],
        'keywords': [],
        'auto_parse_interval': 300
    })

@app.route('/api/parse-thailand', methods=['POST'])
def parse_thailand():
    try:
        from bot_parser import run_bot_parser
        result = run_bot_parser()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/thailand-channels')
def get_thailand_channels():
    channels_file = 'thailand_channels.json'
    if os.path.exists(channels_file):
        with open(channels_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({})

@app.route('/bot/webhook', methods=['POST'])
def bot_webhook():
    from telegram_bot import handle_start, handle_app, send_message
    
    data = request.json
    if not data:
        return jsonify({'ok': True})
    
    message = data.get('message', {})
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    user = message.get('from', {})
    user_name = user.get('first_name', 'друг')
    
    if not chat_id:
        return jsonify({'ok': True})
    
    if text == '/start':
        handle_start(chat_id, user_name)
    elif text == '/app':
        handle_app(chat_id)
    elif text == '/help':
        send_message(chat_id, '🦌 <b>Goldantelope ASIA</b>\n\n/start - Главное меню\n/app - Открыть приложение\n/thailand - Тайланд\n/vietnam - Вьетнам')
    elif text == '/thailand':
        send_message(chat_id, '🇹🇭 <b>Тайланд</b>\n\n70+ каналов:\n- Пхукет\n- Паттайя\n- Бангкок\n- Самуи\n\nНажмите /app чтобы открыть!')
    elif text == '/vietnam':
        send_message(chat_id, '🇻🇳 <b>Вьетнам</b>\n\nКаналы скоро будут добавлены!\n\nНажмите /app чтобы открыть!')
    elif text == '/auth':
        send_message(chat_id, '🔐 <b>Авторизация Telethon</b>\n\nКод был отправлен в приложение Telegram на номер +84342893121.\n\nНайдите сообщение от "Telegram" с 5-значным кодом и отправьте его сюда!')
    elif text and text.isdigit() and len(text) == 5:
        with open('pending_code.txt', 'w') as f:
            f.write(text)
        send_message(chat_id, f'✅ Код {text} получен! Пробую авторизацию...')
    
    return jsonify({'ok': True})

@app.route('/bot/setup', methods=['POST'])
def setup_bot_webhook():
    import requests
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    domains = os.environ.get('REPLIT_DOMAINS', '')
    
    if domains:
        webhook_url = f"https://{domains.split(',')[0]}/bot/webhook"
        url = f'https://api.telegram.org/bot{bot_token}/setWebhook'
        result = requests.post(url, data={'url': webhook_url}).json()
        return jsonify(result)
    
    return jsonify({'error': 'No domain found'})

# ============ УПРАВЛЕНИЕ КАНАЛАМИ ============

def load_channels(country):
    """Загрузить каналы для страны"""
    channels_file = f'{country}_channels.json'
    if os.path.exists(channels_file):
        with open(channels_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('channels', {})
    return {}

def save_channels(country, channels):
    """Сохранить каналы для страны"""
    channels_file = f'{country}_channels.json'
    with open(channels_file, 'w', encoding='utf-8') as f:
        json.dump({'channels': channels}, f, ensure_ascii=False, indent=2)

@app.route('/api/admin/channels', methods=['GET'])
def get_channels():
    """Получить список каналов по странам"""
    country = request.args.get('country', 'vietnam')
    channels = load_channels(country)
    return jsonify({'country': country, 'channels': channels})

@app.route('/api/admin/add-channel', methods=['POST'])
def add_channel():
    """Добавить канал"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category', 'chat')
    channel = request.json.get('channel', '').strip().replace('@', '')
    
    if not channel:
        return jsonify({'error': 'Channel name required'}), 400
    
    channels = load_channels(country)
    
    if category not in channels:
        channels[category] = []
    
    if channel in channels[category]:
        return jsonify({'error': 'Channel already exists'}), 400
    
    channels[category].append(channel)
    save_channels(country, channels)
    
    return jsonify({'success': True, 'message': f'Канал @{channel} добавлен в {category}'})

@app.route('/api/admin/remove-channel', methods=['POST'])
def remove_channel():
    """Удалить канал"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category')
    channel = request.json.get('channel')
    
    channels = load_channels(country)
    
    if category in channels and channel in channels[category]:
        channels[category].remove(channel)
        save_channels(country, channels)
        return jsonify({'success': True, 'message': f'Канал @{channel} удален'})
    
    return jsonify({'error': 'Channel not found'}), 404

@app.route('/api/bunny-image/<path:image_path>')
def bunny_image_proxy(image_path):
    """Прокси для загрузки изображений из BunnyCDN Storage"""
    import urllib.parse
    
    storage_zone = os.environ.get('BUNNY_CDN_STORAGE_ZONE', 'storage.bunnycdn.com')
    storage_name = os.environ.get('BUNNY_CDN_STORAGE_NAME', 'goldantelope')
    api_key = os.environ.get('BUNNY_CDN_API_KEY', '')
    
    # Decode the path and fetch from storage
    decoded_path = urllib.parse.unquote(image_path)
    url = f'https://{storage_zone}/{storage_name}/{decoded_path}'
    
    try:
        r = requests.get(url, headers={'AccessKey': api_key}, timeout=30)
        if r.status_code == 200:
            content_type = r.headers.get('Content-Type', 'image/jpeg')
            return Response(r.content, mimetype=content_type, headers={
                'Cache-Control': 'public, max-age=86400'
            })
        else:
            return Response('Image not found', status=404)
    except Exception as e:
        print(f"Error fetching image: {e}")
        return Response('Error fetching image', status=500)

# ============ УПРАВЛЕНИЕ ГОРОДАМИ ============

def load_cities_config(country, category):
    """Загрузить конфигурацию городов для категории"""
    cities_file = f'cities_{country}_{category}.json'
    if os.path.exists(cities_file):
        with open(cities_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_cities_config(country, category, cities):
    """Сохранить конфигурацию городов"""
    cities_file = f'cities_{country}_{category}.json'
    with open(cities_file, 'w', encoding='utf-8') as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)

@app.route('/api/admin/cities', methods=['GET', 'POST'])
def get_cities():
    """Получить города для категории (требует авторизации)"""
    # Для GET запросов проверяем пароль в параметрах
    if request.method == 'GET':
        password = request.args.get('password', '')
    else:
        password = request.json.get('password', '')
    
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.args.get('country', 'vietnam') if request.method == 'GET' else request.json.get('country', 'vietnam')
    category = request.args.get('category', 'restaurants') if request.method == 'GET' else request.json.get('category', 'restaurants')
    cities = load_cities_config(country, category)
    return jsonify({'country': country, 'category': category, 'cities': cities})

@app.route('/api/admin/add-city', methods=['POST'])
def add_city():
    """Добавить город"""
    password = request.form.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.form.get('country', 'vietnam')
    category = request.form.get('category', 'restaurants')
    name = request.form.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'City name required'}), 400
    
    cities = load_cities_config(country, category)
    
    # Генерируем ID
    city_id = f"{country}_{category}_{len(cities)}_{int(time.time())}"
    
    # Обработка фото
    image_path = '/static/icons/placeholder.png'
    photo = request.files.get('photo')
    if photo and photo.filename:
        import base64
        file_data = photo.read()
        ext = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else 'jpg'
        
        # Сохраняем в static/icons/cities/
        os.makedirs('static/icons/cities', exist_ok=True)
        filename = f"{city_id}.{ext}"
        filepath = f"static/icons/cities/{filename}"
        with open(filepath, 'wb') as f:
            f.write(file_data)
        image_path = f"/static/icons/cities/{filename}"
    
    new_city = {
        'id': city_id,
        'name': name,
        'image': image_path
    }
    
    cities.append(new_city)
    save_cities_config(country, category, cities)
    
    return jsonify({'success': True, 'message': f'Город "{name}" добавлен'})

@app.route('/api/admin/update-city', methods=['POST'])
def update_city():
    """Обновить название города"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category', 'restaurants')
    city_id = request.json.get('city_id')
    name = request.json.get('name', '').strip()
    
    cities = load_cities_config(country, category)
    
    for city in cities:
        if city.get('id') == city_id:
            city['name'] = name
            save_cities_config(country, category, cities)
            return jsonify({'success': True, 'message': 'Город обновлён'})
    
    return jsonify({'error': 'City not found'}), 404

@app.route('/api/admin/update-city-photo', methods=['POST'])
def update_city_photo():
    """Обновить фото города"""
    password = request.form.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.form.get('country', 'vietnam')
    category = request.form.get('category', 'restaurants')
    city_id = request.form.get('city_id')
    photo = request.files.get('photo')
    
    if not photo or not photo.filename:
        return jsonify({'error': 'Photo required'}), 400
    
    cities = load_cities_config(country, category)
    
    for city in cities:
        if city.get('id') == city_id:
            file_data = photo.read()
            ext = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else 'jpg'
            
            os.makedirs('static/icons/cities', exist_ok=True)
            filename = f"{city_id}.{ext}"
            filepath = f"static/icons/cities/{filename}"
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            city['image'] = f"/static/icons/cities/{filename}"
            save_cities_config(country, category, cities)
            return jsonify({'success': True, 'message': 'Фото обновлено'})
    
    return jsonify({'error': 'City not found'}), 404

@app.route('/api/admin/delete-city', methods=['POST'])
def delete_city():
    """Удалить город"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    category = request.json.get('category', 'restaurants')
    city_id = request.json.get('city_id')
    
    cities = load_cities_config(country, category)
    
    for i, city in enumerate(cities):
        if city.get('id') == city_id:
            cities.pop(i)
            save_cities_config(country, category, cities)
            return jsonify({'success': True, 'message': 'Город удалён'})
    
    return jsonify({'error': 'City not found'}), 404

# ============ РУЧНОЙ ПАРСЕР ============

@app.route('/api/admin/manual-parse', methods=['POST'])
def manual_parse():
    """Ручной парсинг канала - 100% всех сообщений"""
    password = request.json.get('password', '')
    admin_key = os.environ.get('ADMIN_KEY', '29Sept1982!')
    
    if password != admin_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    country = request.json.get('country', 'vietnam')
    channel = request.json.get('channel', '').strip().replace('@', '')
    category = request.json.get('category', 'chat')
    limit = request.json.get('limit', 0)  # 0 = все сообщения
    
    if not channel:
        return jsonify({'error': 'Channel name required'}), 400
    
    try:
        # Пытаемся использовать Telethon парсер
        from telethon.sync import TelegramClient
        
        api_id = os.environ.get('TELEGRAM_API_ID')
        api_hash = os.environ.get('TELEGRAM_API_HASH')
        
        if not api_id or not api_hash:
            return jsonify({'error': 'Telegram API credentials not configured'}), 400
        
        session_name = 'goldantelope_manual'
        client = TelegramClient(session_name, int(api_id), api_hash)
        
        count = 0
        log_messages = []
        
        with client:
            entity = client.get_entity(channel)
            
            # Если limit=0, загружаем ВСЕ сообщения (iter_messages без limit)
            if limit == 0 or limit >= 10000:
                messages = client.iter_messages(entity)
            else:
                messages = client.iter_messages(entity, limit=limit)
            
            data = load_data(country)
            if category not in data:
                data[category] = []
            
            existing_ids = set(item.get('telegram_link', '') for item in data[category])
            
            for msg in messages:
                if msg.text:
                    telegram_link = f"https://t.me/{channel}/{msg.id}"
                    
                    # Пропускаем дубликаты
                    if telegram_link in existing_ids:
                        continue
                    
                    # Создаём объявление
                    listing_id = f"{country}_{category}_{int(time.time())}_{count}"
                    
                    new_listing = {
                        'id': listing_id,
                        'title': msg.text[:100] if msg.text else 'Без названия',
                        'description': msg.text,
                        'date': msg.date.isoformat() if msg.date else datetime.now().isoformat(),
                        'telegram_link': telegram_link,
                        'category': category
                    }
                    
                    # Обработка фото - пересылаем в наш Telegram канал
                    if msg.photo:
                        try:
                            # Скачиваем фото во временный буфер
                            import io
                            photo_buffer = io.BytesIO()
                            client.download_media(msg.photo, file=photo_buffer)
                            photo_buffer.seek(0)
                            image_data = photo_buffer.read()
                            
                            if image_data:
                                # Отправляем в Telegram канал с полным текстом
                                caption = f"📋 {new_listing['title']}\n\n{msg.text[:900] if msg.text else ''}"
                                file_id = send_photo_to_channel(image_data, caption)
                                
                                if file_id:
                                    new_listing['telegram_file_id'] = file_id
                                    new_listing['telegram_photo'] = True
                                    # Получаем актуальный URL
                                    fresh_url = get_telegram_photo_url(file_id)
                                    if fresh_url:
                                        new_listing['image_url'] = fresh_url
                                    log_messages.append(f"[✓] Фото #{count+1} загружено в Telegram канал")
                        except Exception as photo_err:
                            log_messages.append(f"[!] Ошибка фото: {photo_err}")
                    
                    data[category].insert(0, new_listing)
                    existing_ids.add(telegram_link)
                    count += 1
                    
                    if count % 50 == 0:
                        log_messages.append(f"[{count}] Обработано {count} сообщений...")
            
            save_data(country, data)
        
        return jsonify({
            'success': True, 
            'message': f'Парсинг завершён. Добавлено {count} объявлений из канала @{channel}.',
            'count': count,
            'log': '\n'.join(log_messages[-30:])
        })
        
    except ImportError:
        return jsonify({'error': 'Telethon не установлен. Используйте Bot API.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ TELEGRAM КАНАЛ ДЛЯ ФОТО ============

TELEGRAM_PHOTO_CHANNEL = '-1003577636318'

def send_photo_to_channel(image_data, caption=''):
    """Отправить фото в Telegram канал и получить file_id для постоянного хранения"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("TELEGRAM: Bot token not found!")
        return None
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        files = {'photo': ('photo.jpg', image_data, 'image/jpeg')}
        data = {
            'chat_id': TELEGRAM_PHOTO_CHANNEL,
            'caption': caption[:1024] if caption else ''
        }
        
        print(f"TELEGRAM: Sending photo to channel {TELEGRAM_PHOTO_CHANNEL}, size: {len(image_data)} bytes")
        response = requests.post(url, files=files, data=data, timeout=30)
        result = response.json()
        print(f"TELEGRAM: Response: {result}")
        
        if result.get('ok'):
            photo = result['result'].get('photo', [])
            if photo:
                largest = max(photo, key=lambda x: x.get('file_size', 0))
                file_id = largest.get('file_id')
                print(f"TELEGRAM: Photo uploaded! file_id: {file_id[:50]}...")
                return file_id
        else:
            print(f"TELEGRAM: Failed to send photo: {result.get('description', 'Unknown error')}")
        
        return None
    except Exception as e:
        print(f"TELEGRAM: Error sending photo to channel: {e}")
        return None

def get_telegram_photo_url(file_id):
    """Получить актуальный URL фото по file_id"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token or not file_id:
        return None
    
    try:
        file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        file_response = requests.get(file_url, timeout=10).json()
        
        if file_response.get('ok'):
            file_path = file_response['result'].get('file_path')
            return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    except:
        pass
    return None

# ============ ВНУТРЕННИЙ ЧАТ С TELEGRAM АВТОРИЗАЦИЕЙ ============

CHAT_DATA_FILE = 'internal_chat.json'
CHAT_BLACKLIST_FILE = 'chat_blacklist.json'
verification_codes = {}
import random
import string

def load_chat_data():
    if os.path.exists(CHAT_DATA_FILE):
        with open(CHAT_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = data.get('messages', [])
            three_days_ago = datetime.now() - timedelta(days=3)
            messages = [m for m in messages if datetime.fromisoformat(m.get('timestamp', '2000-01-01')) > three_days_ago]
            return {'messages': messages[-500:], 'users': data.get('users', {})}
    return {'messages': [], 'users': {}}

def save_chat_data(data):
    three_days_ago = datetime.now() - timedelta(days=3)
    data['messages'] = [m for m in data.get('messages', []) if datetime.fromisoformat(m.get('timestamp', '2000-01-01')) > three_days_ago][-500:]
    with open(CHAT_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_blacklist():
    if os.path.exists(CHAT_BLACKLIST_FILE):
        with open(CHAT_BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'users': []}

def save_blacklist(data):
    with open(CHAT_BLACKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

CHAT_USERS_FILE = 'chat_users.json'

def load_chat_users():
    if os.path.exists(CHAT_USERS_FILE):
        with open(CHAT_USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_chat_users(data):
    with open(CHAT_USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def find_chat_id_by_username(username):
    users = load_chat_users()
    username_lower = username.lower().replace('@', '')
    if username_lower in users:
        return users[username_lower]
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return None
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates?limit=100"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            updates = resp.json().get('result', [])
            for upd in updates:
                msg = upd.get('message', {})
                user = msg.get('from', {})
                uname = user.get('username', '').lower()
                chat_id = msg.get('chat', {}).get('id')
                if uname and chat_id:
                    users[uname] = str(chat_id)
            save_chat_users(users)
            if username_lower in users:
                return users[username_lower]
    except Exception as e:
        print(f"Error finding chat_id: {e}")
    return None

@app.route('/api/chat/request-code', methods=['POST'])
def request_chat_code():
    data = request.json
    username = data.get('telegram_id', '').strip().replace('@', '')
    if not username:
        return jsonify({'success': False, 'error': 'Укажите ваш @username'})
    
    blacklist = load_blacklist()
    if username.lower() in [u.lower() for u in blacklist.get('users', [])]:
        return jsonify({'success': False, 'error': 'Ваш аккаунт заблокирован'})
    
    chat_id = find_chat_id_by_username(username)
    if not chat_id:
        return jsonify({'success': False, 'error': 'Сначала напишите боту @goldantelope_bot команду /start'})
    
    code = ''.join(random.choices(string.digits, k=6))
    verification_codes[username.lower()] = {'code': code, 'expires': datetime.now() + timedelta(minutes=10), 'chat_id': chat_id}
    
    message = f"🔐 Ваш код для чата GoldAntelope:\n\n<b>{code}</b>\n\nКод действителен 10 минут."
    
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if bot_token:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            resp = requests.post(url, json={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}, timeout=10)
            if resp.status_code == 200 and resp.json().get('ok'):
                return jsonify({'success': True, 'message': 'Код отправлен в Telegram'})
            else:
                error_desc = resp.json().get('description', 'Ошибка отправки')
                return jsonify({'success': False, 'error': f'Ошибка Telegram: {error_desc}'})
    except Exception as e:
        print(f"Chat code error: {e}")
    
    return jsonify({'success': False, 'error': 'Не удалось отправить код'})

@app.route('/api/chat/verify-code', methods=['POST'])
def verify_chat_code():
    data = request.json
    telegram_id = data.get('telegram_id', '').strip().replace('@', '').lower()
    code = data.get('code', '').strip()
    
    if not telegram_id or not code:
        return jsonify({'success': False, 'error': 'Укажите ID и код'})
    
    stored = verification_codes.get(telegram_id)
    if not stored:
        return jsonify({'success': False, 'error': 'Сначала запросите код'})
    
    if datetime.now() > stored['expires']:
        del verification_codes[telegram_id]
        return jsonify({'success': False, 'error': 'Код истёк, запросите новый'})
    
    if stored['code'] != code:
        return jsonify({'success': False, 'error': 'Неверный код'})
    
    del verification_codes[telegram_id]
    
    session_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    chat_data = load_chat_data()
    chat_data['users'][session_token] = {'telegram_id': telegram_id, 'created': datetime.now().isoformat()}
    save_chat_data(chat_data)
    
    return jsonify({'success': True, 'token': session_token, 'username': telegram_id})

@app.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    chat_data = load_chat_data()
    return jsonify({'messages': chat_data.get('messages', [])[-500:]})

@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    data = request.json
    token = data.get('token', '')
    message = data.get('message', '').strip()
    
    if not token or not message:
        return jsonify({'success': False, 'error': 'Требуется авторизация'})
    
    if len(message) > 2000:
        return jsonify({'success': False, 'error': 'Сообщение слишком длинное (макс 2000 символов)'})
    
    chat_data = load_chat_data()
    user = chat_data.get('users', {}).get(token)
    if not user:
        return jsonify({'success': False, 'error': 'Сессия истекла, войдите заново'})
    
    telegram_id = user.get('telegram_id', 'Аноним')
    
    blacklist = load_blacklist()
    if telegram_id.lower() in [u.lower() for u in blacklist.get('users', [])]:
        return jsonify({'success': False, 'error': 'Ваш аккаунт заблокирован'})
    
    new_message = {
        'id': f"msg_{int(time.time())}_{random.randint(1000,9999)}",
        'username': telegram_id,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    chat_data['messages'].append(new_message)
    save_chat_data(chat_data)
    
    return jsonify({'success': True})

@app.route('/api/admin/chat-blacklist', methods=['GET', 'POST'])
def admin_chat_blacklist():
    admin_key = request.headers.get('X-Admin-Key') or request.json.get('admin_key') if request.json else None
    expected_key = os.environ.get('ADMIN_KEY', 'goldantelope2025')
    if admin_key != expected_key:
        return jsonify({'success': False, 'error': 'Неверный пароль'}), 401
    
    if request.method == 'GET':
        return jsonify(load_blacklist())
    
    data = request.json
    action = data.get('action')
    username = data.get('username', '').strip().replace('@', '').lower()
    
    if not username:
        return jsonify({'success': False, 'error': 'Укажите username'})
    
    blacklist = load_blacklist()
    
    if action == 'add':
        if username not in blacklist['users']:
            blacklist['users'].append(username)
            save_blacklist(blacklist)
        return jsonify({'success': True, 'message': f'{username} добавлен в чёрный список'})
    elif action == 'remove':
        blacklist['users'] = [u for u in blacklist['users'] if u.lower() != username]
        save_blacklist(blacklist)
        return jsonify({'success': True, 'message': f'{username} удалён из чёрного списка'})
    
    return jsonify({'success': False, 'error': 'Неизвестное действие'})

@app.route('/api/admin/chat-delete', methods=['POST'])
def admin_delete_chat_message():
    data = request.json
    admin_key = data.get('admin_key')
    expected_key = os.environ.get('ADMIN_KEY', 'goldantelope2025')
    if admin_key != expected_key:
        return jsonify({'success': False, 'error': 'Неверный пароль'}), 401
    
    msg_id = data.get('message_id')
    if not msg_id:
        return jsonify({'success': False, 'error': 'Укажите ID сообщения'})
    
    chat_data = load_chat_data()
    chat_data['messages'] = [m for m in chat_data['messages'] if m.get('id') != msg_id]
    save_chat_data(chat_data)
    
    return jsonify({'success': True, 'message': 'Сообщение удалено'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
