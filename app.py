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
    filtered = listings
    
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
    
    if category == 'transport':
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
            price = item.get('price')
            if price is None:
                return 0
            if isinstance(price, (int, float)):
                return int(price)
            # Извлекаем числа из строки (например, "6 000 000" или "6,5 млн")
            try:
                price_str = str(price).lower()
                multiplier = 1
                
                # Check for million indicator
                if 'млн' in price_str or 'mln' in price_str:
                    multiplier = 1000000
                
                # Replace comma with dot for decimal parsing (6,5 -> 6.5)
                price_str = price_str.replace(',', '.')
                # Remove spaces and non-numeric chars except dot
                price_str = re.sub(r'[^\d.]', '', price_str)
                # Handle multiple dots - keep only first
                parts = price_str.split('.')
                if len(parts) > 2:
                    price_str = parts[0] + '.' + ''.join(parts[1:])
                
                if price_str:
                    return int(float(price_str) * multiplier)
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
        return jsonify(filtered)
    
    # Сортировка по дате - новые сверху
    filtered.sort(key=lambda x: x.get('date', x.get('added_at', '1970-01-01')) or '1970-01-01', reverse=True)
    
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
        listing['id'] = f"{country}_realestate_{int(time.time())}"
        listing['status'] = 'approved'
        data = load_data(country)
        if 'real_estate' not in data:
            data['real_estate'] = []
        data['real_estate'].insert(0, listing)
        save_data(country, data)
        return jsonify({'success': True, 'message': 'Объявление одобрено'})
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
