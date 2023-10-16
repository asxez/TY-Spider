from urllib.parse import urljoin, urlparse

import requests
from loguru import logger

import config


class RobotsParser:
    def __init__(self, user_agent: str = config.engine_name_en):
        self.user_agent = user_agent
        self.rules = {}

    def fetch_robots_txt(self, base_url: str) -> str:
        try:
            url = urljoin(base_url, "/robots.txt")
            res = requests.get(url, headers={'user-agent': self.user_agent})
            res.raise_for_status()
            return res.text
        except requests.RequestException as e:
            logger.error(f'获取robots.txt文件时出错：{e}')
            return ''

    def parser_robots_txt(self, robots_txt: str) -> None:
        lines = robots_txt.split('\n')
        current_agent = None

        for line in lines:
            line = line.strip()

            if line.startswith('User-agent:'):
                current_agent = line.split(': ')[-1]
                self.rules[current_agent] = {'allow': [], 'disallow': []}
            elif line.startswith('Disallow:'):
                if current_agent is not None:
                    self.rules[current_agent]['disallow'].append(line.split(': ')[-1])
            elif line.startswith('Allow:'):
                if current_agent is not None:
                    self.rules[current_agent]['allow'].append(line.split(': ')[-1])

    def can_crawl(self, url: str) -> bool:
        parser_url = urlparse(url)
        base_url = f'{parser_url.scheme}://{parser_url.netloc}'

        if base_url not in self.rules:
            robots_txt = self.fetch_robots_txt(base_url)
            self.parser_robots_txt(robots_txt)
        if base_url in self.rules:
            rules = self.rules[base_url]
            for path in rules['disallow']:
                if url.startswith(urljoin(base_url, path)):
                    return False
            for path in rules['allow']:
                if url.startswith(urljoin(base_url, path)):
                    return True
        return True


if __name__ == '__main__':
    robots = RobotsParser()
    boo = robots.can_crawl('https://www.baidu.com')
    if boo:
        print('ok')
    else:
        print('no')
