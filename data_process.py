from typing import Any, Union

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import stop_words


def tfidf(texts: list, querys: list) -> Union[Any, None]:
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


def remove_stop_words(ori_list:list) -> list:
    words = set(stop_words)
    return [item for item in ori_list if item not in words]
