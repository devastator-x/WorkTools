import geoip2.database
import socket
import re
import urllib.parse
import requests
import os
from flask_paginate import Pagination, get_page_args
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from modules.County_Codes import country_code_to_korean

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
    url = "https://api.cognitive.microsoft.com/bing/v7.0/news/search"
    headers = {"Ocp-Apim-Subscription-Key": os.getenv("ec6fd8d4f6cb4263be9c7062fd398f91")}
    params = {
        "q": "해킹 OR 해커 OR 멀웨어 OR 취약점",
        "count": 50,
        "freshness": "Day",
        "textFormat": "Raw",
        "safeSearch": "Off"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    news_data = response.json()["value"]

    # Convert published time to datetime object
    for news in news_data:
        news["datePublished"] = datetime.strptime(news["datePublished"], "%Y-%m-%dT%H:%M:%S.%fZ")

    # Paginate news
    total = len(news_data)
    pagination_news = news_data[offset: offset + per_page]
    pagination = Pagination(page=page, per_page=per_page, total=total,
                            css_framework='bootstrap4')

    return render_template('news.html', news=pagination_news, page=page,
                           per_page=per_page, pagination=pagination)

if __name__ == '__main__':
    app.run()
