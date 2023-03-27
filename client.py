import requests
import time


response = requests.post('http://127.0.0.1:5000/upscale', files={'image': open('upscale/lama_300px.png', 'rb')})
task_id = response.json()['task_id']

while True:
    response = requests.get(f'http://127.0.0.1:5000/tasks/{task_id}').json()
    status = response['status']
    if status != 'PENDING':
        result_path = response['result']
        requests.get(f'http://127.0.0.1:5000/processed/{result_path}')
        break
    else:
        time.sleep(0.1)
