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
from lxml import etree

from config import engine_name_en, bing_api, wiki, target_depth, db_name, data_col_name
from database import MongoDB
from log_lg import SpiderLog
from mongodb import save_data

_headers = {
    'User-Agent': engine_name_en
}


class RobotsParser:
    def __init__(self, user_agent: str = engine_name_en):
        self.user_agent = user_agent
        self.rules = {}

    def fetch_robots_txt(self, base_url: str) -> str:
        try:
            url = urljoin(base_url, "/robots.txt")
            res = requests.get(url, headers={'user-agent': self.user_agent}, timeout=3)
            if res.status_code != 200:
                return ""
            res.raise_for_status()
            return res.text
        except Exception as e:
            logger.error(f'获取robots.txt文件时出错：{e}')
            return ""

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


def get_bing_response(question: Any) -> str:
    try:
        response = requests.get(bing_api.format(q=question), headers=_headers, timeout=4).text
    except Exception as e:
        logger.error(f'获取必应响应出错：{e}')
    else:
        return response


def parse_bing_response(text: str) -> list[dict]:
    datas = []
    doc = etree.HTML(text)
    elements = doc.xpath('//*[@id="b_results"]/li')
    for element in elements:
        try:
            href = element.xpath('./h2/a/@href')[0]
            description = element.xpath('./div[2]/p/text()')[0]
            title = element.xpath('./h2/a/text() | ./h2/a/strong/text()')
            title = "".join(title)
            datas.append({
                "title": title,
                "description": description,
                "href": href,
                "keywords": ""
            })
        except IndexError as e:
            logger.error(f'解析必应响应出错:{e}')
    return datas


def parse_page_url(text: str) -> dict[str, str]:
    ph = {}
    doc = etree.HTML(text)
    elements = doc.xpath('//*[@id="b_results"]/li/nav/ul/li')
    for element in elements:
        try:
            page = element.xpath('./a/@aria-label')[0]
            href = element.xpath('./a/@href')[0]
            href = "https://www4.bing.com" + href
            ph[page] = href
        except Exception as e:  # 可能存在多种类型的错误
            logger.error(f'解析页面链接出错：{e}')
    return ph


def get_other_page_response(urls: dict) -> list[list[dict]]:
    datas = []
    for page, url in urls.items():
        try:
            data = parse_bing_response(requests.get(url, headers=_headers, timeout=3).text)
        except Exception as e:
            logger.error(f'获取其他页出错：{e}')
        else:
            logger.info(f'获取 {page} 响应成功')
            datas.append(data)
    return datas


def get_keywords_and_description(url: str) -> Union[list[dict[str, str | None]], None]:
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

            datas.append({
                "title": title,
                "keywords": keywords_content,
                "description": description_content,
                "href": url
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


def _save_bfs_state(visited: set, queue: deque, file_name: str) -> None:
    state_data = (visited, queue)
    try:
        with open(f'./temp/{file_name}.pkl', 'wb') as f:
            pickle.dump(state_data, f)
    except Exception as e:
        logger.error(f'保存pkl文件失败：{e}')


def _load_bfs_state(file_name: str) -> tuple[Any, Any] | tuple[None, None]:
    try:
        with open(f'./temp/{file_name}.pkl', 'rb') as f:
            visited, queue = pickle.load(f)
        if visited and queue:
            return visited, queue
        else:
            return None, None
    except Exception as e:
        logger.error(f'加载bfs状态时出错：{e}')


def bfs(start: str, file_name: str, target_depth: int = 2) -> None:
    visited, queue = _load_bfs_state(file_name) or (set(), deque([(start, 0)]))
    robots_parser = RobotsParser(user_agent=engine_name_en)
    with MongoDB(db_name, data_col_name) as db:
        col = db.col

        while queue:
            url, depth = queue.popleft()

            if robots_parser.can_crawl(url):
                if depth > target_depth:
                    break
                if url in visited:
                    continue

                visited.add(url)
                logger.info(f"深度：{depth}，链接：{url}，process：{multiprocessing.current_process().name}")

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
                    save_data(data, col)
                _save_bfs_state(visited, queue, file_name)
                time.sleep(random.uniform(1, 2))
            else:
                logger.warning(f'{url}不允许爬')
                continue


if __name__ == '__main__':
    SpiderLog()

    processes = []
    p2 = multiprocessing.Process(target=bfs, args=(wiki, "wiki", target_depth))
    processes.append(p2)
    p2.start()

    p3 = multiprocessing.Process(target=bfs, args=("https://www.asxe.vip", 'asxe', target_depth))
    processes.append(p3)
    p3.start()

    for p in processes:
        p.join()
