import pickle
import random
import time
from collections import deque
from typing import Union, Any

import requests
from bs4 import BeautifulSoup
from loguru import logger
from lxml import etree

from config import engine_name_en
from database import MongoDB
from error import Error, RequestError, IIndexError
from mongodb import save_data
from robots import RobotsParser

headers = {
    'User-Agent': engine_name_en
}


def get_bing_response(question: Any) -> str:
    try:
        response = requests.get(config.bing_api.format(q=question), headers=headers).text
    except Error as e:
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
                'title': title,
                'description': description,
                'href': href,
                'word': ''
            })
        except Error as e:
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
        except Error as e:  # 可能存在多种类型的错误
            logger.error(f'解析页面链接出错：{e}')
    return ph


def get_other_page_response(urls: dict) -> list[list[dict]]:
    datas = []
    for page, url in urls.items():
        try:
            data = parse_bing_response(requests.get(url, headers=headers).text)
        except Error as e:
            logger.error(f'获取其他页出错：{e}')
        else:
            logger.info(f'获取 {page} 响应成功')
            datas.append(data)
    return datas


def get_keywords_and_description(url: str) -> Union[list[dict[str, str | None]], None]:
    datas = []
    no_datas = ['', None, ' ']
    try:
        response = requests.get(url, headers=headers, timeout=5)
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
                'title': title,
                'word': keywords_content,
                'description': description_content,
                'href': url
            })
            return datas
    except Error as e:
        logger.error(f"获取 {url} 信息出错：{e}")
    return None


def get_links_from_url(url: str) -> list[str]:
    if not url.startswith('http'):
        return []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True)]
            return links
    except RequestError as e:
        logger.error(f"访问 {url} 出错：{e}")
    return []


def in_wiki(query: str) -> bool:
    try:
        response = requests.get(config.wiki + '/wiki/' + query, headers=headers, timeout=5)
        if '目前还没有与上述标题相同的条目' in response.text:
            return False
        return True
    except RequestError as e:
        logger.error(f'检测维基百科收录出现错误{e}')


bfs_state_file = './temp/state_file.pkl'


def save_bfs_state(visited: set, get: set, queue: deque) -> None:
    state_data = (visited, get, queue)
    try:
        with open(bfs_state_file, 'wb') as f:
            pickle.dump(state_data, f)
    except Error as e:
        logger.error(f'保存pkl文件失败：{e}')


def load_bfs_state() -> tuple[Any, Any, Any] | tuple[None, None, None]:
    try:
        with open(bfs_state_file, 'rb') as f:
            visited, get, queue = pickle.load(f)
        if visited and get and queue:
            return visited, get, queue
        else:
            return None, None, None
    except Error as e:
        logger.error(f'加载bfs状态时出错：{e}')


def bfs(start: str, target_depth: int = 2) -> None:
    # visited = set()
    # get = set()
    # queue = deque([(start, 0)])  # 存储(URL, 深度)的队列
    visited, get, queue = load_bfs_state() or (set(), set(), deque([(start, 0)]))
    robots_parser = RobotsParser(user_agent=config.engine_name_en)
    with MongoDB() as db:
        col = db.col

        while queue:
            url, depth = queue.popleft()

            if robots_parser.can_crawl(url):
                if depth > target_depth:
                    break
                if url in visited:
                    continue

                visited.add(url)
                logger.info(f"深度：{depth}, 链接：{url}")

                links = get_links_from_url(url)
                for link in links:
                    if link.startswith('/'):
                        link = start + link
                    try:
                        link = 'http' + link.split('http')[2]  # 获取到的链接存在一点问题，暂时用这个方法解决
                    except IIndexError:
                        pass
                    if link in get:
                        continue
                    get.add(link)
                    queue.append((link, depth + 1))
                    if ('wiki' in link and '.org' in link) or (not link.startswith('http')):  # 去除维基百科和非链接
                        continue
                    data = get_keywords_and_description(link)
                    if data is None:
                        continue
                    else:
                        save_data(data, col)
                    # with open('./temp/bfs.txt', 'a', encoding='utf-8') as f:
                    #   f.write(f'{link}\n')
                save_bfs_state(visited, get, queue)
                time.sleep(random.uniform(2.0, 3.0))
            else:
                logger.warning(f'{url}不允许爬')
                continue


if __name__ == '__main__':
    start_url = config.wiki
    bfs(start_url, config.target_depth)
