import os

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jieba import lcut_for_search
from loguru import logger

from config import fastapi_port, db_name, data_col_name
from data_process import remove_stop_words, TFIDF
from database import MongoDB
from log_lg import ServerLog
from mongodb import search_data, save_data, creat_index
from spider import get_bing_response, get_other_page_response, parse_page_url, parse_bing_response

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def not_question() -> dict[str, str | int]:
    return {
        "status": 2,
        "response": "未输入内容"
    }


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/show/", response_class=HTMLResponse)
async def get_show(request: Request):
    return templates.TemplateResponse("show.html", {"request": request})


@app.post("/search/", response_class=JSONResponse)
async def search(q: str = Form()) -> dict[str, str | int]:
    with MongoDB(db_name, data_col_name) as db:
        col = db.col

        if not q:
            not_question()

        list_question = lcut_for_search(q)
        list_question = remove_stop_words(list_question)
        temp_results = []
        temp_results_rank = []

        if os.path.exists("./temp/q.txt"):
            with open("./temp/q.txt", "r", encoding="utf-8") as f1:
                text = f1.read()
            if str(q) in text:
                logger.info("数据存在，开始检索")
                for question in list_question:
                    results = search_data(question, col)
                    for result in results:
                        temp_results.append(result)

                texts = [str(doc["title"]) + " " + str(doc["description"]) + " " + str(doc["keywords"]) for doc in
                         temp_results]
                ranked_indices = TFIDF(texts, list_question)

                for rank, index in enumerate(ranked_indices):
                    temp_results_rank.append(temp_results[index])
                return {
                    "status": 1,
                    "response": str(temp_results_rank[0:1000])
                }

        logger.info("数据不存在，开始爬")
        try:
            os.makedirs("./temp/")
        except OSError:
            pass
        with open("./temp/q.txt", "a", encoding="utf-8") as f2:
            f2.write(f"{q} ")

        bing_res = get_bing_response(q)
        datas = parse_bing_response(bing_res)
        save_data(datas, col)
        datas = get_other_page_response(parse_page_url(bing_res))
        for data in datas:
            save_data(data, col)

        for question in list_question:
            results = search_data(question, col)
            for result in results:
                temp_results.append(result)

        texts = [str(doc["title"]) + " " + str(doc["description"]) + " " + str(doc["keywords"]) for doc in temp_results]
        ranked_indices = TFIDF(texts, list_question)

        for rank, index in enumerate(ranked_indices):
            temp_results_rank.append(temp_results[index])
        return {
            "status": 1,
            "response": str(temp_results_rank[0:1000])
        }


if __name__ == "__main__":
    ServerLog()
    with MongoDB(db_name, data_col_name) as db:
        creat_index(db.col)
    config = uvicorn.Config("server:app", port=fastapi_port, log_level="info")
    server = uvicorn.Server(config)
    server.run()
