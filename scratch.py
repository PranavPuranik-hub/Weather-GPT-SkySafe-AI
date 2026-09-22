import requests

try:
    state = requests.get('http://localhost:8000/api/decision/state').json()
    print('Wards:', len(state['wards']))
    print('Allocations:', len(state['allocations']))
except Exception as e:
    print(e)
