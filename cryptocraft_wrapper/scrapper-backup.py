import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
mydb = mysql.connector.connect(
    host='158.196.145.50',       
    user='crypto',   
    password='Crypto2022',
    database='coinmarketcap', 
    port = 3307
)
cursor = mydb.cursor()

def webscrapper(date):
    url_date = date.strftime("%b%d.%Y").lower()
    url = f'https://www.cryptocraft.com/calendar?day={url_date}'
    print(url)
    scraper = cloudscraper.create_scraper()
    page = scraper.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')

    calendar = soup.find_all('table')[-1]
    print(calendar)
    #calendar_titles = calendar.find_all('th').get('class')
    calendar_titles = [
        title.get('class')[0] for title in calendar.find_all('th') if title.get('class')
    ]

    rows = []
    time = None
    current_date = date
    previous_time = None
    
    sql = """
                INSERT INTO events (date, time, impact, name, actual, forecast, previous) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
    for tr in calendar.find_all('tr'):
        print(tr.get("class"))
        if "calendar__row" in tr.get("class", []):
            cells = tr.find_all('td')
            if len(cells)>1:
                row = [current_date]
                for cell in cells:
                    # Najdeme čas (calendar__time)
                    if 'calendar__time' in cell.get('class', []):
                        time = cell.text.strip()  # Text času
                        if time == '':
                            time = previous_time
                        else:
                            previous_time = time
                        row.append(time)
                        print(time)
                        continue
                    # Najdeme impakt (calendar__impact)
                    if 'calendar__impact' in cell.get('class', []):
                        impact_span = cell.find('span')
                        impact = impact_span.get('class')[1]
                        if 'red' in impact:
                            impact = 'high'
                            row.append(impact)
                        elif 'ora' in impact:
                            impact = 'medium'
                            row.append(impact)
                        elif 'yel' in impact:
                            impact = 'low'
                            row.append(impact)
                        elif 'gra' in impact:
                            impact = 'none'
                            row.append(impact)
                        print(impact)
                        continue
                    if 'calendar__event' in cell.get('class', []):
                        event = cell.text.strip() 
                        row.append(event)
                        continue
                    if 'calendar__actual' in cell.get('class', []):
                        actual = cell.text.strip()
                        row.append(actual)
                        continue
                    if 'calendar__forecast' in cell.get('class', []):
                        forecast = cell.text.strip()  
                        row.append(forecast)
                        continue
                    if 'calendar__previous' in cell.get('class', []):
                        previous = cell.text.strip()  
                        row.append(previous)
                        print(previous)
                        continue
                rows.append(row)
                if time is not None:
                    values = (
                    current_date, time, impact, event, actual, forecast, previous)
                    cursor.execute(sql, values)
                
                
    mydb.commit()
    
start_date = datetime.strptime("2024-08-30", "%Y-%m-%d")
end_date = datetime.strptime("2026-03-22", "%Y-%m-%d")

current_date = start_date
while current_date <= end_date:   
    webscrapper(current_date)
    current_date += timedelta(days=1)
#df = pd.DataFrame(columns=calendar_titles)
#print(calendar.find_all('tr'))
#https://www.cryptocraft.com/calendar