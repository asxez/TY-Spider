from typing import Any

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jieba import lcut_for_search

from config import fastapi_port, db_name, data_col_name, key_col_name
from data_process import remove_stop_words, TFIDF
from database import MongoDB
from log_lg import ServerLog
from mongodb import creat_index, search_key, find_all, search_data

origins = [
    "http://localhost:1314",
    "http://127.0.0.1:1314",
]

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=origins)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_data_use_key(list_question: list[str]) -> list[dict[str, Any]]:
    with MongoDB(db_name, key_col_name) as key_db:
        key_col = key_db.col
        indexes = [result['value'] for question in list_question for result in search_key(question, key_col)]
    indexes = list(set(sum(indexes, [])))

    with MongoDB(db_name, data_col_name) as db_data:
        col_data = db_data.col
        all_data = list(find_all(col_data, projection={'_id': 0}))

    answer = [all_data[index] for index in indexes]
    return answer


def get_data_use_search(list_question: list[str]) -> list[dict[str, Any]]:
    with MongoDB(db_name, data_col_name) as data_db:
        data_col = data_db.col
        temp_results = [result for question in list_question for result in search_data(question, data_col)]
    return temp_results


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/show/", response_class=HTMLResponse)
async def get_show(request: Request):
    return templates.TemplateResponse("show.html", {"request": request})


@app.post("/search/", response_class=JSONResponse)
async def search(q: str = Form()):
    if not q:
        return {
            "status": 2,
            "response": "未输入内容"
        }

    list_question = lcut_for_search(q)
    list_question = remove_stop_words(list_question)

    key_ans = get_data_use_key(list_question)
    search_ans = get_data_use_search(list_question)

    all_ans = key_ans.copy()
    for item in search_ans:
        if item not in all_ans:
            all_ans.append(item)

    texts = [str(doc["title"]) + " " + str(doc["description"]) + " " + str(doc["keywords"]) for doc in all_ans]
    try:
        ranked_indices = TFIDF(texts, list_question)
    except ValueError:
        return {
            'status': 3,
            'response': '无效'
        }
    len_ranked_indices = len(ranked_indices)

    for rank, index in enumerate(ranked_indices):
        all_ans[index]['weight'] = all_ans[index]['weight'] + (len_ranked_indices - rank) * 0.09

    ans_sorted = sorted(all_ans, key=lambda x: x['weight'], reverse=True)
    return {
        'status': 1,
        'response': str(ans_sorted)
    }


if __name__ == "__main__":
    ServerLog()
    with MongoDB(db_name, data_col_name) as db:
        creat_index(db.col)
    config = uvicorn.Config("server:app", port=fastapi_port, log_level="info")
    server = uvicorn.Server(config)
    server.run()
