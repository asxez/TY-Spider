from collections import defaultdict
from time import sleep
from typing import Any, Union

from jieba import lcut_for_search
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import stop_words, db_name, key_col_name
from database import MongoDB
from mongodb import save_data
from utils import cost_time


class ReverseIndex:
    def __init__(self):
        self.index = defaultdict()

    @cost_time
    def build_index(self, doc: list) -> bool:
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
                self.index[word].append(doc_id)
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
                result.update(self.index[word])
        return list(result)

    def get_index(self) -> dict:
        return self.index


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


def remove_stop_words(ori_list: list) -> list:
    words = set(stop_words)
    return [item for item in ori_list if item not in words]
