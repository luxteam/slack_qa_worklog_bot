from urllib.parse import urlencode
import urllib.request as urlrequest
import json
from config import WEBHOOK_URL


def notify(**kwargs):
    # send message to slack api
    return send(kwargs)

def send(payload):
    # send payload to slack api
    url = WEBHOOK_URL
    opener = urlrequest.build_opener(urlrequest.HTTPHandler())
    payload_json = json.dumps(payload)
    data = urlencode({"payload": payload_json})
    req = urlrequest.Request(url)
    response = opener.open(req, data.encode('utf-8')).read()
    return response.decode('utf-8')