#!/usr/bin/env python3

import koji
import sys
import requests
from time import sleep
from bs4 import BeautifulSoup
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER = "subbotin"
HOME_DIR = "/home/" + USER
USERSTRING = "Alexandr Subbotin <alexander.subbotin@red-soft.ru>"
TAG = "os73-updates"

accepted_fields = [
    'ID',
    'Package Name',
    'Version',
    'Release',
    'Summary',
    'Description',
    'Changelog'
]


class Parser:

    def __init__(self, start_url):
        self.cookies = {
        }
        self.headers = {
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.167 Safari/537.36',
        }
        self.params = [
        ]
        self.start_url = start_url

    @staticmethod
    def _get(*args, **kwargs) -> BeautifulSoup:
        while True:
            try:
                response: requests.Response = requests.get(*args, **kwargs)
                # проверим код ответа
                if response.status_code != requests.codes.ok:
                    print(response.status_code)
                    raise ConnectionError
                sleep(0.1)
                return BeautifulSoup(response.text, 'lxml')
            except ConnectionError as CE:
                # Стучимся пока не соединимся.
                print(f'Ошибка соединения {CE}')
                sleep(0.250)

    def run(self):
        soup = self._get(self.start_url,
                         params=self.params,
                         cookies=self.cookies,
                         headers=self.headers,
                         verify=False)
        build_data = self._parse_build_page(soup)
        json_data = json.dumps(build_data, indent=4)
        print(json_data)

    @staticmethod
    def _parse_build_page(soup: BeautifulSoup) -> dict:
        result = {}
        build_table = soup.find('table')
        for tr in build_table.select('tr'):
            name = tr.find("th").text if tr.find("th") else None
            data = tr.find("td").text if tr.find("td") else None
            if not name or name not in accepted_fields:
                continue
            if name == 'ID':
                result['build_id'] = data
                continue
            elif name == 'Package Name':
                data = tr.find("a").text
            elif name == 'Changelog':
                # сплитим по двойной новой строке
                # в случае пустого поля в конце списка - отрезаем его
                data = data.split('\n\n')[:-1] \
                    if not data.split('\n\n')[-1] else data.split('\n\n')
            result[name] = data
        return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Wrong argument")
        exit(1)
    else:
        package_name = sys.argv[1].split('.', 1)[0]
        session = koji.ClientSession("http://stapel.red-soft.ru/kojihub")
        kojitag = session.getTag(TAG)
        package_list = session.getLatestRPMS(kojitag['id'], arch='src', package=package_name)[0]
        package = package_list[0] if package_list else None
        if package_list:
            package = package_list[0]
            START_URL = f"http://stapel.red-soft.ru/koji/buildinfo?buildID={str(package['build_id'])}"
            parser = Parser(START_URL)
            parser.run()
        else:
            print("No packages found")
            exit(0)
