import geoip2.database
import socket
import re
import urllib.parse
import requests
import os
import shodan as shodan_lib
import ipaddress
from flask_paginate import Pagination, get_page_args
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from modules.County_Codes import country_code_to_korean
from dateutil.parser import parse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pytz import timezone

def get_unique_words(title):
    # 여기서는 제목을 공백으로 분리하여 단어를 추출하였습니다.
    # 필요에 따라 더 복잡한 토큰화 도구를 사용할 수 있습니다.
    return set(title.split(' '))

# 국가 코드를 한국어 국가 이름으로 변환하는 함수
def get_korean_country_name(country_code):
    return country_code_to_korean.get(country_code, 'None')

app = Flask(__name__)

# GeoLite2 데이터베이스 파일의 경로를 지정합니다.
reader = geoip2.database.Reader('GeoLite2-Country.mmdb')

def get_ip_address(input_value):
    try:
        if not input_value.replace(".", "").isnumeric():  # If it's a domain name
            ip_address = socket.gethostbyname(input_value)
            return ip_address
        else:  # If it's an IP address
            return input_value
    except socket.gaierror:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    ip_data = []

    if request.method == 'POST':
        input_list = request.form['ip_list'].splitlines()

        for input_value in input_list:
            ip_address = get_ip_address(input_value)
            if ip_address is None:
                ip_data.append({
                    'ip': 'Invalid IP or Domain',
                    'country': 'Invalid IP or Domain'
                })
            else:
                try:
                    response = reader.country(ip_address)
                    ip_data.append({
                        'ip': input_value,
                        'country': get_korean_country_name(response.country.iso_code)  # 수정된 부분
                    })
                except:
                    ip_data.append({
                        'ip': input_value,
                        'country': 'Invalid IP'
                    })

    return render_template('index.html', ip_data=ip_data)

@app.route('/ascii_to_char', methods=['GET', 'POST'])
def ascii_to_char():
    characters = ''
    if request.method == 'POST':
        ascii_string = request.form.get('ascii_string')
        ascii_codes = re.findall(r'\d+', ascii_string)
        for ascii_code in ascii_codes:
            ascii_code = int(ascii_code)
            if ascii_code >= 0 and ascii_code <= 127:
                characters += chr(ascii_code)
    return render_template('ascii_to_char.html', characters=characters)

@app.route('/utf8_decoder', methods=['GET', 'POST'])
def utf8_decoder():
    decoded_string = ''
    if request.method == 'POST':
        encoded_string = request.form.get('encoded_string')
        decoded_string = urllib.parse.unquote(encoded_string)
    return render_template('utf8_decoder.html', decoded_string=decoded_string)

@app.route('/news', methods=['GET'])
def news():
    # Get page info from request
    page, per_page, offset = get_page_args(page_parameter='page',
                                           per_page_parameter='per_page')
    
    # Bing Search v7 API endpoint
    subscription_key = os.environ['BING_SEARCH_V7_SUBSCRIPTION_KEY']
    url = 'https://api.bing.microsoft.com/v7.0/news/search'
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    days = request.args.get('days', default='Day')
    
    # Get the topics from the form
    topics = request.args.getlist('topics')
    days = request.args.get('days', default='Day')

    # If no topics selected, set a default
    if not topics:
        topics = ["보안"]

    # Generate the query string
    query = " OR ".join(topics)

    params = {
        "q": query,
		"mkt": "ko-KR",
        "count": 100,
        "freshness": days,
        "textFormat": "Raw",
        "safeSearch": "Off"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    news_data = response.json()["value"]

    def get_unique_words(title):
        return set(title.split(' '))

    unique_news_data = []
    for news in news_data:
        title = news['name']
        unique_words = get_unique_words(title)

        if any(sum(word in get_unique_words(existing_news['name']) for word in unique_words) >= 2 for existing_news in unique_news_data):
            continue

        unique_news_data.append(news)

    # Convert published time to datetime object
    for news in unique_news_data:
        # Convert the 'datePublished' string to a datetime object
        date_published = parse(news["datePublished"])
        # Format the datetime object to a string with only the date
        news["datePublished"] = date_published.strftime('%Y-%m-%d')
    
    # Paginate news
    total = len(unique_news_data)
    pagination_news = unique_news_data[offset: offset + per_page]
    pagination = Pagination(page=page, per_page=per_page, total=total,
                            css_framework='bootstrap4')

    return render_template('news.html', news=pagination_news, page=page,
                           per_page=per_page, pagination=pagination, selected_topics=topics, days=days)

@app.route('/shodan', methods=['GET', 'POST'])
def shodan():
    results = None
    template_name = 'shodan.html'
    
    if request.method == 'POST':
        query = request.form.get('query')
        if not query:
            results = "Please enter an IP address or a domain name."
        else:
            shodan_api_key = os.environ['shodanAPI_key']  # Replace with your Shodan API Key
            api = shodan_lib.Shodan(shodan_api_key)

            try:
                ipaddress.ip_address(query)
                # If the above line of code doesn't raise an exception, it means that the input is a valid IP address
                try:
                    results = api.host(query)
                except shodan_lib.APIError as e:
                    results = f"No information available for that IP: {query}"
            except ValueError:
                # If the input is not a valid IP address, it might be a domain name
                try:
                    results = api.search(query)
                    template_name = 'shodan_domain.html'  # Use a different template for domain names
                except shodan_lib.APIError as e:
                    results = f"Error: {e}"
            except shodan_lib.APIError as e:
                results = f"Error: {e}"


    return render_template(template_name, results=results)

@app.route('/krcert')
def krcert():
    url = "https://www.krcert.or.kr/kr/bbs/list.do?menuNo=205020&bbsId=B0000133"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('div', {'class': 'tbl'}).find('table')
    if table is None:
        return "Table not found on the page."

    rows = table.find_all('tr')[1:]  # get all rows except the header row
    posts = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 5:
            title_tag = cols[1].find('a')
            date_tag = cols[4]
            
            # Check if title_tag or date_tag is None before calling get_text
            if title_tag is None or date_tag is None:
                continue

            title = title_tag.get_text(strip=True)
            date = date_tag.get_text(strip=True)

            post_date = datetime.strptime(date, "%Y-%m-%d")

            if (datetime.now() - post_date).total_seconds() <= 518400:
                posts.append((title, date))

    if not posts:
        return "No new posts in the last 48 hours."

    return render_template('krcert.html', posts=posts)

if __name__ == '__main__':
    app.run()
