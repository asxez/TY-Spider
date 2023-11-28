import requests

data = {
    'q': 'test'
}
res = requests.post('http://127.0.0.1:1314/search/', data=data)
print(res.text)
