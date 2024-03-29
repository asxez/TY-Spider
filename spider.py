import multiprocessing
import pickle
import random
import time
from collections import deque
from typing import Union, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import (
    engine_name_en,
    wiki,
    db_name,
    data_col_name,
    spider_check_memory,
    bloom_dataSize,
    bloom_errorRate,
)
from database import MongoDB
from mongodb import save_data
from utils import (
    Memory,
    Schedule,
    check_lang,
    ParserLink,
    BloomFilter,
)

_headers = {
    'User-Agent': engine_name_en
}


class RobotsParser:
    def __init__(self, user_agent: str = engine_name_en):
        self._user_agent = user_agent
        self._rules = {}

    def _fetch_robots_txt(self, base_url: str) -> str:
        try:
            url = urljoin(base_url, "/robots.txt")
            res = requests.get(url, headers={'user-agent': self._user_agent}, timeout=3)
            if res.status_code != 200:
                return ""
            res.raise_for_status()
            return res.text
        except Exception as e:
            logger.error(f'获取robots.txt文件时出错：{e}')
            return ""

    def _parser_robots_txt(self, robots_txt: str) -> None:
        lines = robots_txt.split('\n')
        current_agent = None

        for line in lines:
            line = line.strip()

            if line.startswith('User-agent:'):
                current_agent = line.split(': ')[-1]
                self._rules[current_agent] = {'allow': [], 'disallow': []}
            elif line.startswith('Disallow:'):
                if current_agent is not None:
                    self._rules[current_agent]['disallow'].append(line.split(': ')[-1])
            elif line.startswith('Allow:'):
                if current_agent is not None:
                    self._rules[current_agent]['allow'].append(line.split(': ')[-1])

    def can_crawl(self, url: str) -> bool:
        parser_url = urlparse(url)
        base_url = f'{parser_url.scheme}://{parser_url.netloc}'

        if base_url not in self._rules:
            robots_txt = self._fetch_robots_txt(base_url)
            self._parser_robots_txt(robots_txt)
        if base_url in self._rules:
            rules = self._rules[base_url]
            for path in rules['disallow']:
                if url.startswith(urljoin(base_url, path)):
                    return False
            for path in rules['allow']:
                if url.startswith(urljoin(base_url, path)):
                    return True
        return True


def get_keywords_and_description(url: str) -> Union[list[dict[str, Any]], None]:
    datas = []
    no_datas = ['', None, ' ']
    try:
        response = requests.get(url, headers=_headers, timeout=4)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            keywords = soup.find('meta', attrs={"name": "keywords"})
            description = soup.find('meta', attrs={"name": "description"})
            title = soup.find('title')

            title = title.text if title else None
            keywords_content: str = keywords['content'] if keywords else ''
            description_content: str = description['content'] if description else ''

            if title in no_datas:
                logger.info(f'{url} 的title为空')
                return None

            lang, weight = check_lang(title + " " + keywords_content + " " + description_content)
            if lang == 'zh':
                datas.append({
                    "title": title,
                    "keywords": keywords_content,
                    "description": description_content,
                    "href": url,
                    "weight": 0.5,
                    "netloc": ParserLink(url).netloc
                })
                return datas
            datas.append({
                "title": title,
                "keywords": keywords_content,
                "description": description_content,
                "href": url,
                "weight": weight if weight < 0.5 else 1 - weight,
                "netloc": ParserLink(url).netloc
            })
            return datas
    except Exception as e:
        logger.error(f"获取 {url} 信息出错：{e}")
    return None


def get_links_from_url(url: str) -> list[str]:
    if not url.startswith('http'):
        return []
    try:
        response = requests.get(url, headers=_headers, timeout=4)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True)]
            return links
    except Exception as e:
        logger.error(f"访问 {url} 出错：{e}")
    return []


def in_wiki(query: str) -> bool:
    try:
        response = requests.get(wiki + '/wiki/' + query, headers=_headers, timeout=4)
        if '目前还没有与上述标题相同的条目' in response.text:
            return False
        return True
    except Exception as e:
        logger.error(f'检测维基百科收录出现错误{e}')


def _save_bfs_state(queue: deque, file_name: str) -> None:
    state_data = queue
    try:
        with open(f'./temp/{file_name}.pkl', 'wb') as f:
            pickle.dump(state_data, f)
    except Exception as e:
        logger.error(f'保存pkl文件失败：{e}')


def _load_bfs_state(file_name: str) -> deque | None:
    try:
        with open(f'./temp/{file_name}.pkl', 'rb') as f:
            queue = pickle.load(f)
        if queue:
            return queue
        return None
    except Exception as e:
        logger.error(f'加载queue状态时出错：{e}')


def bfs(start: str, file_name, target_depth: int = 2) -> None:
    visited = BloomFilter(bloom_dataSize, bloom_errorRate)
    queue = _load_bfs_state(file_name) or deque([(start, 0)])
    robots_parser = RobotsParser(user_agent=engine_name_en)
    with MongoDB(db_name, data_col_name) as db:
        col = db.col

        while queue:
            if spider_check_memory:
                Schedule().schedule_interval(
                    [
                        {
                            'function': Memory().canuse_memory_percentage,
                            'seconds': 10
                        }
                    ], 0.1
                )

            url, depth = queue.popleft()

            if robots_parser.can_crawl(url):
                if depth > target_depth:
                    break
                if url in visited:
                    continue

                visited.add(url)
                logger.info(f"深度：{depth}，链接：{url}，process：{multiprocessing.current_process().name}")

                this_data = get_keywords_and_description(url)
                if this_data is None:
                    continue
                weight = this_data[0]['weight'] if this_data[0]['weight'] >= 0.5 else 1 - this_data[0]['weight']  # 确保加权

                links = get_links_from_url(url)
                for link in links:
                    if link.startswith('/'):
                        link = start + link
                    try:
                        link = 'http' + link.split('http')[2]  # 获取到的链接存在一点问题，暂时用这个方法解决
                    except IndexError:
                        pass
                    queue.append((link, depth + 1))
                    if ('wiki' in link and '.org' in link) or (not link.startswith('http')):  # 去除维基百科和非链接
                        continue
                    data = get_keywords_and_description(link)
                    if data is None:
                        continue
                    if data[0]['weight'] == 0.5:  # 增权，是中文则增权更多，反之少
                        data[0]['weight'] = (data[0]['weight'] + weight * 1.1) / 2
                    else:
                        data[0]['weight'] = (data[0]['weight'] + weight * 0.9) / 2
                    save_data(data, col)
                _save_bfs_state(queue, file_name)
                time.sleep(random.uniform(0.3, 0.9))
            else:
                logger.warning(f'{url}不允许爬')
                continue
