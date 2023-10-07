import requests
import json

data = {
    'q': '前端开发'
}
res = requests.post('http://127.0.0.1:1314/search/', data=data)
print(res.text)
