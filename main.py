import hmac
import hashlib
import json
import requests
import time
from tradingview_ta import TA_Handler, Interval

# Данные для подключения к API Bybit
API_KEY = 'Your  API'
API_SECRET = 'Your_secret'
BASE_URL = 'https://api.bybit.com'

# Данные для Telegram-бота
TELEGRAM_TOKEN = 'your_token'
TELEGRAM_CHAT_ID = '@your_chat_id'

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
        params["stopLoss"] = format(round(stop_loss, 3), '.3f')

    # Добавляем параметр тейк-профита, если он указан
    if take_profit:
        params["takeProfit"] = format(round(take_profit, 3), '.3f')

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
                # Получение значения индикатора RSi, SMA20 и EMA20
                sma_value = analysis.indicators.get("SMA20", None)
                ema_value = analysis.indicators.get("EMA20", None)
                rci_value = analysis.indicators.get("RSI", None)
                print(rci_value)  # отладочный вывод
                # Отладка значения RSI
                # print(f"Значение RSI для {symbol}: {rci_value}")
                if rci_value is None or sma_value is None or ema_value is None:
                    print(f"Нет значения одного из индикаторов для {
                          symbol}. Пропуск.")
                else:
                    # Проверка на условия RSI для отправки сигнала
                    if rci_value > 70:
                        message = f"Новый сигнал: ПРОДАЖА для {
                            symbol} на основе RSI (значение: {rci_value})"
                        side = "Sell"
                    elif rci_value < 30:
                        message = f"Новый сигнал: ПОКУПКА для {
                            symbol} на основе RSI (значение: {rci_value})"
                        side = "Buy"
                    else:
                        message = None

                    if message:
                        # Расчет стоп-лосса и тейк-профита на основе значений SMA20 и EMA20
                        if side == "Buy":
                            # Устанавливаем стоп-лосс ниже значения SMA или EMA
                            stop_loss = min(sma_value, ema_value)
                            take_profit = round(get_current_price(
                                symbol) + (get_current_price(symbol) - stop_loss) * 1.5, 3)
                        elif side == "Sell":
                            # Устанавливаем стоп-лосс выше значения SMA или EMA
                            stop_loss = max(sma_value, ema_value)
                            take_profit = round(get_current_price(
                                symbol) - (stop_loss - get_current_price(symbol)) * 1.5, 3)
                         # Временно используем SMA для расчета стоп-лосса
                        if stop_loss:
                            percent_to_stop_loss = abs(
                                (get_current_price(symbol) - stop_loss) / get_current_price(symbol) * 100)
                            leverage = int(100 / percent_to_stop_loss)
                            print(f"Расчетное кредитное плечо для {
                                  symbol}: {leverage}")
                            # Установка кредитного плеча перед размещением ордера
                            set_leverage(symbol, leverage)

                        # Отправка уведомления в Telegram
                        print(f"Отправка сообщения: {message}")
                        send_telegram_message(message)

                        # Размещение ордера (количество можно изменить при необходимости)
                        # qty = 1  # Количество можно менять в зависимости от стратегии
                        # place_order(symbol, side, qty, stop_loss=stop_loss)
            else:
                print(f"Не удалось получить текущую цену для {
                      symbol}. Пропуск.")

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
