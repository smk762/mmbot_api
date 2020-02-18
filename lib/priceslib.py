#!/usr/bin/env python3
import json
import time
import requests
import datetime

import logging

logger = logging.getLogger()

def format_num_10f(val):
    if val != 0:
        try:
            val = "{:.10f}".format(round(float(val),10))
        except:
            pass
    return val
    
def get_paprika_history(coin_id, since='year_ago', quote='usd'):
    intervals = ['5m', '10m', '15m', '30m', '45m', '1h', '2h', '3h', '6h', '12h', '24h', '1d', '7d', '14d', '30d', '90d', '365d']
    quotes = ['usd', 'btc']
    now = datetime.datetime.now()
    timestamp = datetime.datetime.timestamp(now)
    if since == 'day_ago':
        timestamp = timestamp-(24*60*60)
        interval = '15m'
    elif since == 'week_ago':
        timestamp = timestamp-(7*24*60*60)
        interval = '2h'
    elif since == 'month_ago':
        timestamp = timestamp-(30*24*60*60)
        interval = '6h'
    elif since == '3_month_ago':
        timestamp = timestamp-(3*30*24*60*60)
        interval = '12h'
    elif since == '6_month_ago':
        timestamp = timestamp-(6*30*24*60*60)
        interval = '1d'
    elif since == 'year_ago':
        timestamp = timestamp-(365*24*60*60)
        interval = '1d'
    url = "https://api.coinpaprika.com/v1/tickers/"+coin_id+"/historical?start="+str(int(timestamp))+"&quote="+quote+"&interval="+interval
    #print("getting paprika api history")
    r = requests.get(url)
    return r.json()


## REFACTORED FOR API

def get_forex(base='USD'):
    #print("getting forex")
    url = 'https://api.exchangerate-api.com/v4/latest/'+base
    r = requests.get(url)
    return r

# TODO: parse https://api.coingecko.com/api/v3/coins/list for supported coins api-codes
def gecko_prices(coin_ids, fiat):
    #print("getting gecko api prices")
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = dict(ids=str(coin_ids),vs_currencies=fiat)
    r = requests.get(url=url, params=params)
    return r

def coinspot_prices():
    r = requests.get('https://www.coinspot.com.au/pubapi/latest')
    return r

# TODO: parse https://api.coinpaprika.com/v1/coins for supported coins api-codes
def get_paprika_price(coin_id):
    #print("getting paprika api prices")
    url = 'https://api.coinpaprika.com/v1/ticker/'+coin_id
    r = requests.get(url)
    return r
