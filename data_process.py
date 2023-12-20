from collections import defaultdict
from time import sleep
from typing import Any, Union

import requests
from bs4 import BeautifulSoup
from jieba import lcut_for_search
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import stop_words, db_name, key_col_name, engine_name_en
from database import MongoDB
from mongodb import save_data
from utils import cost_time, is_url


class ReverseIndex:
    """
    反向索引构建器
    """

    def __init__(self):
        # {'key': [index]}
        self.index = defaultdict()

    @cost_time
    def build_index(self, doc: list, rank: int) -> bool:
        if len(doc) < 20:
            return False
        words = []
        for doc_id, data in enumerate(doc):
            try:
                words.extend(remove_stop_words(lcut_for_search(data['title'])))
                words.extend(remove_stop_words(lcut_for_search(data['keywords'])))
                words.extend(remove_stop_words(lcut_for_search(data['description'])))
            except Exception:
                continue
            for word in words:
                if word not in self.index:
                    self.index[word] = []
                self.index[word].append(20 * rank + doc_id)
        return True

    @cost_time
    def save_index(self) -> None:
        with MongoDB(db_name, key_col_name) as db:
            for key, value in self.index.items():
                save_data(
                    [{'key': key, 'value': value}],
                    db.col
                )
        sleep(2)

    @cost_time
    def search(self, query: str) -> list:
        query_words = lcut_for_search(query)
        query_words = remove_stop_words(query_words)
        result = set()
        for word in query_words:
            if word in self.index:
                result.update(self.index[word])  # 合并集合
        return list(result)

    def get_index(self) -> defaultdict:
        return self.index


class BackLink:
    """
    反向链接整理器
    """

    def __init__(self):
        self.map: defaultdict[str, set[str]] = defaultdict()

    @staticmethod
    def requests(link: str) -> list | None:
        try:
            res = requests.get(link, headers={'user-agent': engine_name_en}, timeout=4)
            res.encoding = 'utf-8'
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                hrefs = [a['href'] for a in soup.find_all('a', href=True) if is_url(a['href'])]
                return hrefs
        except requests.exceptions.RequestException as e:
            logger.warning(f'获取反链时{e}')
            return None

    def add(self, source: str, target: str) -> None:
        """
        source为值，这里源链接的域名，target为源链接所引用的url。
        """
        if target in self.map:
            self.map[target].add(source)
        else:
            self.map[target] = set()
            self.map[target].add(source)

    def __len__(self, key: str) -> int | None:
        if key in self.map:
            return len(self.map[key])
        logger.warning(f'无此键：{key}')


def TFIDF(texts: list, querys: list) -> Union[Any, None]:
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)

    # 计算每个查询与文档的相似性分数
    query_similarity_scores = []
    for query in querys:
        user_query_vector = vectorizer.transform([query])
        similarity_scores = cosine_similarity(user_query_vector, tfidf_matrix)
        query_similarity_scores.append(similarity_scores)

    combined_scores = sum(query_similarity_scores) / len(querys)  # 综合所有查询的分数，计算平均分数
    ranked_indices = combined_scores.argsort()[0][::-1]  # 从高到低排列
    return ranked_indices


def remove_stop_words(ori_list: list) -> list[str]:
    words = set(stop_words)
    return [item for item in ori_list if item not in words]
