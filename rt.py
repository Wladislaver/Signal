import hmac
import hashlib
import json
import requests
import time
from tradingview_ta import TA_Handler, Interval

# Данные для подключения к API Bybit
API_KEY = 'k4jz6FkIRQ83Llsum8'
API_SECRET = 'LEglqzrGBSI9FDz1dpp3QmUOkYPGevKPfLX7'
BASE_URL = 'https://api.bybit.com'

# Данные для Telegram-бота
TELEGRAM_TOKEN = '7703902719:AAEYpM0vWl0Y4Kssu3om3CBF0Jtgo3eZ2J8'
TELEGRAM_CHAT_ID = '@alertslav'

# Функция для отправки сообщения в Telegram


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    # Добавляем отладочный вывод
    # print(f"Отправка сообщения в Telegram: {response.json()}")
    return response.json()

# Функция для установки кредитного плеча на Bybit


def set_leverage(symbol, leverage):
    endpoint = "/v5/position/set-leverage"
    url = BASE_URL + endpoint
    params = {
        "apiKey": API_KEY,
        "symbol": symbol,
        "buyLeverage": leverage,
        "sellLeverage": leverage,
        "timestamp": int(time.time() * 1000)
    }

    # Генерация подписи
    param_str = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(bytes(API_SECRET, "utf-8"),
                         bytes(param_str, "utf-8"), hashlib.sha256).hexdigest()
    params["sign"] = signature

    # Отправка запроса
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=params)
    # Отладка установки кредитного плеча
    print(f"Установка кредитного плеча: {response.json()}")
    return response.json()


# Функция для размещения ордера на Bybit с возможностью установки стоп-лосса и тейк-профита


def place_order(symbol, side, qty, order_type="Market", stop_loss=None, take_profit=None):
    endpoint = "/v5/order/create"
    url = BASE_URL + endpoint
    params = {
        "apiKey": API_KEY,
        "symbol": symbol,
        "side": side,
        "orderType": order_type,
        "qty": qty,
        "timeInForce": "GTC",
        "timestamp": int(time.time() * 1000)
    }

    # Добавляем параметр стоп-лосса, если он указан
    if stop_loss:
        params["stopLoss"] = round(stop_loss, 3)

    # Добавляем параметр тейк-профита, если он указан
    if take_profit:
        params["takeProfit"] = round(take_profit, 3)

    # Генерация подписи
    param_str = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(bytes(API_SECRET, "utf-8"),
                         bytes(param_str, "utf-8"), hashlib.sha256).hexdigest()
    params["sign"] = signature

    # Отправка запроса
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=params)
    print(f"Размещение ордера: {response.json()}")  # Отладка размещения ордера
    return response.json()

# Функция для получения данных о рынке с TradingView с использованием библиотеки tradingview-ta


def get_tradingview_data(symbol):
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange="BYBIT",
        interval=Interval.INTERVAL_15_MINUTES
    )
    try:
        analysis = handler.get_analysis()
        # Отладка данных TradingView
        # print(f"Данные TradingView для {symbol}: {analysis.summary}")
        return analysis
    except Exception as e:
        print(f"Ошибка получения данных от TradingView: {e}")
        return None

# Основной цикл для получения сигналов и отправки уведомлений в Telegram


def main_loop():
    symbols = ["BTCUSDT", "ETHUSDT"]  # Можно расширить список символов
    while True:
        for symbol in symbols:
            analysis = get_tradingview_data(symbol)

            if analysis:
                recommendation = analysis.summary.get(
                    "RECOMMENDATION", "neutral").lower()
                # Используем 20-периодную скользящую среднюю
                sma_value = analysis.indicators.get("SMA20", None)
                # Отладка значения SMA20
                print(f"Значение SMA20 для {symbol}: {sma_value}")
                # Используем 20-периодную экспоненциальную скользящую среднюю
                ema_value = analysis.indicators.get("EMA20", None)
                # Отладка значения SMA20
                print(f"Значение EMA20 для {symbol}: {ema_value}")

                # Проверка наличия значений SMA и EMA
                if sma_value is None or ema_value is None:
                    print(f"Нет значений SMA или EMA для {symbol}. Пропуск.")
                    continue

                # Получение текущей рыночной цены для установки стоп-лосса и тейк-профита
                current_price = get_current_price(symbol)
                print(current_price)

                # Рассчитываем стоп-лосс и тейк-профит на основе SMA и EMA
                if current_price:
                    if recommendation == "buy":
                        # Устанавливаем стоп-лосс ниже значения SMA или EMA
                        stop_loss = min(sma_value, ema_value)
                        # Устанавливаем тейк-профит на 1.5x выше текущей цены
                        take_profit = current_price + \
                            (current_price - stop_loss) * 1.5
                        message = f"Новый сигнал: ПОКУПКА для {symbol} с уровнем стоп-лосса {
                            stop_loss} и тейк-профита {take_profit} (основан на SMA и EMA)"
                        side = "Buy"
                    elif recommendation == "sell":
                        # Устанавливаем стоп-лосс выше значения SMA или EMA
                        stop_loss = max(sma_value, ema_value)
                        # Устанавливаем тейк-профит на 1.5x ниже текущей цены
                        take_profit = current_price - \
                            (stop_loss - current_price) * 1.5
                        message = f"Новый сигнал: ПРОДАЖА для {symbol} с уровнем стоп-лосса {
                            stop_loss} и тейк-профита {take_profit} (основан на SMA и EMA)"
                        side = "Sell"
                    else:
                        continue

                    # Расчет кредитного плеча на основе процента до стоп-лосса
                    percent_to_stop_loss = abs(
                        (current_price - stop_loss) / current_price * 100)
                    # Расчет кредитного плеча и округление в меньшую сторону
                    leverage = int(100 / percent_to_stop_loss)
                    print(f"Расчетное кредитное плечо для {
                          symbol}: {leverage}")

                    # Установка кредитного плеча перед размещением ордера
                    set_leverage(symbol, leverage)

                    # Отправка уведомления в Telegram
                    # Отладка перед отправкой сообщения
                    print(f"Отправка сообщения: {message}")
                    send_telegram_message(message)
            else:
                print(f"Не удалось получить текущую цену для {
                      symbol}. Пропуск.")

                # Размещение ордера (количество можно изменить при необходимости)
                # qty = 1  # Количество можно менять в зависимости от стратегии
                # place_order(symbol, side, qty,
                #             stop_loss=stop_loss, take_profit=take_profit)

        # Задержка перед следующим циклом (например, 5 минут)
        time.sleep(300)

# Функция для получения текущей цены актива


def get_current_price(symbol):
    endpoint = f"/v5/market/tickers?category=linear&symbol={symbol}"
    url = BASE_URL + endpoint
    response = requests.get(url)
    # print(f"Ответ от API: {response.text}")  # Отладка полного ответа
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "list" in data["result"] and len(data["result"]["list"]) > 0:
            ticker_data = data["result"]["list"][0]
            if "lastPrice" in ticker_data:
                # print(f"Текущая цена для {symbol}: {ticker_data['lastPrice']}")
                return float(ticker_data["lastPrice"])
    print(f"Ошибка получения текущей цены для {symbol}: {response.text}")
    return None


if __name__ == '__main__':
    main_loop()
