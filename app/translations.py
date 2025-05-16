# app/translations.py
TRANSLATIONS = {
    'en': {
        'Submit': 'Submit',
        'Delete': 'Delete',
        'Search': 'Search',
        'Street': 'Street',
        'Satellite': 'Satellite',
        'Terrain': 'Terrain',
        'Select crop type': 'Select crop type',
        'Field size (hectares)': 'Field size (hectares)',
        'Planting date': 'Planting date',
        'Add/Edit Crop Report': 'Add/Edit Crop Report',
        'Crop Types': 'Crop Types',
        'Search location...': 'Search location...',
        'Wheat': 'Wheat',
        'Cotton': 'Cotton',
        'Rice': 'Rice',
        'Potato': 'Potato',
        'Corn': 'Corn',
        'Weather': 'Weather',
        'Temperature': 'Temperature',
        'Humidity': 'Humidity',
        'Wind': 'Wind',
        'Precipitation': 'Precipitation',
        'Forecast': 'Forecast',
        'Loading...': 'Loading...',
        'No data available': 'No data available',
        'Error': 'Error',
        'Success': 'Success',
        'Report submitted successfully': 'Report submitted successfully',
        'Failed to submit report': 'Failed to submit report',
        'Location': 'Location',
        'Coordinates': 'Coordinates'
    },
    'uz': {
        'Submit': 'Yuborish',
        'Delete': 'O\'chirish',
        'Search': 'Qidirish',
        'Street': 'Ko\'cha',
        'Satellite': 'Sun\'iy yo\'ldosh',
        'Terrain': 'Relief',
        'Select crop type': 'Ekin turini tanlang',
        'Field size (hectares)': 'Maydon hajmi (gektar)',
        'Planting date': 'Ekish sanasi',
        'Add/Edit Crop Report': 'Ekin hisobotini qo\'shish/tahrirlash',
        'Crop Types': 'Ekin turlari',
        'Search location...': 'Manzilni qidirish...',
        'Wheat': 'Bug\'doy',
        'Cotton': 'Paxta',
        'Rice': 'Guruch',
        'Potato': 'Kartoshka',
        'Corn': 'Makkajo\'xori',
        'Weather': 'Ob-havo',
        'Temperature': 'Harorat',
        'Humidity': 'Namlik',
        'Wind': 'Shamol',
        'Precipitation': 'Yog\'ingarchilik',
        'Forecast': 'Bashorat',
        'Loading...': 'Yuklanmoqda...',
        'No data available': 'Ma\'lumot yo\'q',
        'Error': 'Xato',
        'Success': 'Muvaffaqiyat',
        'Report submitted successfully': 'Hisobot muvaffaqiyatli yuborildi',
        'Failed to submit report': 'Hisobotni yuborishda xatolik yuz berdi',
        'Location': 'Joylashuv',
        'Coordinates': 'Koordinatalar'
    },
    'ru': {
        'Submit': 'Отправить',
        'Delete': 'Удалить',
        'Search': 'Поиск',
        'Street': 'Улица',
        'Satellite': 'Спутник',
        'Terrain': 'Рельеф',
        'Select crop type': 'Выберите тип культуры',
        'Field size (hectares)': 'Размер поля (гектары)',
        'Planting date': 'Дата посадки',
        'Add/Edit Crop Report': 'Добавить/Редактировать отчет',
        'Crop Types': 'Типы культур',
        'Search location...': 'Поиск местоположения...',
        'Wheat': 'Пшеница',
        'Cotton': 'Хлопок',
        'Rice': 'Рис',
        'Potato': 'Картофель',
        'Corn': 'Кукуруза',
        'Weather': 'Погода',
        'Temperature': 'Температура',
        'Humidity': 'Влажность',
        'Wind': 'Ветер',
        'Precipitation': 'Осадки',
        'Forecast': 'Прогноз',
        'Loading...': 'Загрузка...',
        'No data available': 'Нет данных',
        'Error': 'Ошибка',
        'Success': 'Успех',
        'Report submitted successfully': 'Отчет успешно отправлен',
        'Failed to submit report': 'Не удалось отправить отчет',
        'Location': 'Местоположение',
        'Coordinates': 'Координаты'
    }
}


def get_translation(key, lang):
    """Get translation for a key in the specified language.
    
    Args:
        key: The string to translate
        lang: The language code (en, uz, ru)
        
    Returns:
        Translated string or the original key if no translation found
    """
    # Default to English if language not available
    if lang not in TRANSLATIONS:
        lang = 'en'

    # Return translation or the original key if not found
    return TRANSLATIONS[lang].get(key, key)