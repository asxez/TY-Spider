import requests

data = {
    'q': 'test'
}
res = requests.post('http://localhost:1314/search/', data=data)
print(res.text)
