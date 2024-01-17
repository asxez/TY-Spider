import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jieba import lcut_for_search

from config import fastapi_port, db_name, data_col_name, key_col_name
from data_process import remove_stop_words
from database import MongoDB
from log_lg import ServerLog
from mongodb import creat_index, search_key, find_all

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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

    indexes = []
    list_question = lcut_for_search(q)
    list_question = remove_stop_words(list_question)

    with MongoDB(db_name, key_col_name) as key_db:
        key_col = key_db.col
        for question in list_question:
            results = search_key(question, key_col)
            for result in results:
                indexes.append(result['value'])
    indexes = list(set(sum(indexes, [])))

    with MongoDB(db_name, data_col_name) as db_data:
        col_data = db_data.col
        all_data = list(find_all(col_data, projection={'_id': 0}))

    answer = []
    for index in indexes:
        answer.append(all_data[index])

    sort_ans = sorted(answer, key=lambda x: x['weight'], reverse=True)
    return {
        'status': 1,
        'response': str(sort_ans)
    }


if __name__ == "__main__":
    ServerLog()
    with MongoDB(db_name, data_col_name) as db:
        creat_index(db.col)
    config = uvicorn.Config("server:app", port=fastapi_port, log_level="info")
    server = uvicorn.Server(config)
    server.run()
