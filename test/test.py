import requests
import json

data = {
    'q':'中医'
}
res = requests.post('http://127.0.0.1:1314/search',data=data).text
print(json.loads(res).get('response'))