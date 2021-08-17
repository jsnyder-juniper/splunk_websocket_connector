import json
import os
import websocket
import requests
import logging
import sys
import urllib3
import ssl
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
websocket.enableTrace(True)
msg_received = 0
is_connected = False
logging.basicConfig(filename='websocket_logging.log', filemode='a', level=logging.WARNING)

#   You need to have these environment variables populated.df
# MIST_ENV should be environment details: mist.com, eu.mist.com, gc1.mist.com...
api_token = os.environ.get("MIST_TOKEN")
org_id = os.environ.get("MIST_ORGID")
splunk_url = os.environ.get("SPLUNK_URL")
splunk_auth = os.environ.get("SPLUNK_AUTH")
mist_environ = os.environ.get("MIST_ENV")
level = logging.WARN
sites = []


def on_message(ws, message):
    global msg_received
    #print('onmessage', message)
    data = json.loads(message)
    #print(data)
    #for key in data.keys():
    #    if key != "data":
    #        data2[key] = data[key]
    if data['channel'] != "/test":
        #pp.pprint(data)
        try:
            data2 = {}
            data2['event'] = json.loads(data['data'])
            #print(type(data2['event']))
            #data2['fields'] = list(data2['event'].keys())
            data.pop("data")
            data.pop("event")
            data2['sourcetype'] = '_json'
            #print("*******JSON*********")
            #print(json.dumps(data2))
            send_to_splunk(data2)
        except Exception as e:
            print(e)
        msg_received += 1




def on_error(ws, error):
    print(f"ERROR: {error}")


def on_close(ws):
    print('##### disconnected from server')
    logging.warning(f"Disconnected from Server: {time.ctime()}")
    print("Retry : %s" % time.ctime())
    time.sleep(2)
    connect_websocket()


def on_open(ws):
    print('onopen')
    sites = get_sites()
    ws.send(json.dumps({"subscribe": f"/test"}))
    for site in sites:
        ws.send(json.dumps({"subscribe": f"/sites/{site}/devices"}))
        ws.send(json.dumps({"subscribe": f"/sites/{site}/stats/devices"}))

def on_ping(wsapp, message):
    print("Got a ping!")

def on_pong(wsapp, message):
    print("Got a pong! No need to respond")


def send_to_splunk(data: dict):
    print("Sending to splunk")
    headers = {"Authorization": splunk_auth}
    try:
        response = requests.post(splunk_url, headers=headers, data=json.dumps(data), verify=False)
        print(response.text, str(response.status_code))
    except Exception as e:
        print(e)
        print(response.text, str(response.status_code))


def get_sites():
    global api_token
    global org_id
    global sites
    results = []
    print("getting sites")
    try:
        headers = {'Authorization': f'token {api_token}', 'Accept': 'application/json'}
        data = requests.get(f"https://api.mist.com/api/v1/orgs/{org_id}/sites", headers=headers)

        #print(f"Data Retrieved {data.url}")
        #print(data.json())
        for entry in data.json():
            results.append(entry['id'])
    except Exception as e:
        print(e)
        sys.exit()

    #print(results)
    return results


def connect_websocket():
    websocket.enableTrace(True)
    wsapp = websocket.WebSocketApp(f"wss://api-ws.{mist_environ}/v1/stream",
                                   header=[f'Authorization: token {api_token}'],
                                   on_message=on_message,
                                   on_error=on_error,
                                   on_close=on_close,
                                   on_ping=on_ping,
                                   on_pong=on_pong,
                                   on_open=on_open)
    print("Starting Daemon")
    wsapp.run_forever(ping_interval=10, ping_timeout=9, sslopt={"check_hostname": False, "cert_reqs": ssl.CERT_NONE} )


if __name__ == "__main__":
    try:
        connect_websocket()
    except Exception as err:
        print(err)
        print("connect failed")

