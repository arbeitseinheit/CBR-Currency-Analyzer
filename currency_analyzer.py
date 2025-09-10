import httpx
import asyncio
import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict
from lxml import etree


"""Запрашиваем курсы валют на определенную дату"""
async def get_currency_rates(date_str: str, client: httpx.AsyncClient):
    url = f"http://www.cbr.ru/scripts/XML_daily_eng.asp?date_req={date_str}"
    try:
        response = await client.get(url)
        response.raise_for_status()
        return date_str, response.text
    except httpx.RequestError as exc:
        return date_str, None
    except Exception as exc:
        return date_str, None


"""Парсим XML данные и извлекаем курсы валют"""
def parse_currency_xml(xml_data: str, date_str: str) -> List[Dict[str, Any]]:
    rates = []
    
    try:
        root = etree.fromstring(xml_data.encode('utf-8'))
        for currency in root.findall('Valute'):
            name = currency.find('Name').text
            unit_value = float(currency.find('VunitRate').text.replace(',', '.'))
            
            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
            
            rates.append({
                'date': date_obj.strftime('%Y-%m-%d'),
                'name': name,
                'value': unit_value
            })
    except Exception as e:
        pass
    
    return rates


async def main():
    start_time = time.time()
    
    today = datetime.now()
    all_rates = []
    
    days_to_process = 90
    dates = [today - timedelta(days=i) for i in range(days_to_process)]
    date_strs = [date.strftime('%d/%m/%Y') for date in dates]
    
    timeout = httpx.Timeout(30.0)
    processed_count = 0

    # Создаем асинхронный клиент и готовим задачи для одновременного запуска
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [get_currency_rates(date_str, client) for date_str in date_strs]
        
        # asyncio.as_completed запускает все задачи и возвращает их по мере завершения
        for future in asyncio.as_completed(tasks):
            date_str, xml_data = await future
            if xml_data:
                rates = parse_currency_xml(xml_data, date_str)
                all_rates.extend(rates)
            
            processed_count += 1
            progress_text = f"Обрабатываю данные за последние {days_to_process} дней: {processed_count}/{days_to_process}"
            sys.stdout.write(f"\r{progress_text}")
            sys.stdout.flush()

    print()
    
    end_time = time.time()
    print(f"Данные за {days_to_process} дней обработаны за {end_time - start_time:.2f} сек.")
    
    if not all_rates:
        print("Не удалось получить данные.")
        input("Нажмите Enter для выхода.")
        return
    
    max_rate = max(all_rates, key=lambda x: x['value'])
    min_rate = min(all_rates, key=lambda x: x['value'])

    rates_by_currency = defaultdict(list)
    for rate in all_rates:
        rates_by_currency[rate['name']].append(rate['value'])

    # Рассчитываем и сохраняем средний курс для каждой валюты
    avg_rates = {}
    for name, values in rates_by_currency.items():
        avg_rates[name] = sum(values) / len(values)
    
    print(f"\nМаксимальный курс за весь период: {max_rate['value']:.4f} RUB за {max_rate['name']} ({max_rate['date']})")
    print(f"Минимальный курс за весь период: {min_rate['value']:.4f} RUB за {min_rate['name']} ({min_rate['date']})")
    
    print("\nСредний курс за период для каждой валюты:")
    for name in sorted(avg_rates.keys()):
        print(f"- {name}: {avg_rates[name]:.4f} RUB")
    
    input("\nНажмите Enter для выхода.")


if __name__ == "__main__":
    asyncio.run(main())