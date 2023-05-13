import geoip2.database
import socket
import re
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

if __name__ == '__main__':
    app.run()
