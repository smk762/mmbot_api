#!/usr/bin/env python3
import json
import time
import requests
from . import coinslib, rpclib, binance_api
from statistics import mean
import datetime


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

def get_btc_price(api_key, cointag):
    #print("getting binance btc price for "+cointag)
    if cointag == 'BTC':
        return 1
    else:
        btc_price = binance_api.get_price(api_key, cointag+'BTC')
    if 'price' in btc_price:
        return float(btc_price['price'])
    else:
        return 0

def get_kmd_mm2_price(node_ip, user_pass, coin):
    try:
        #print("getting kmd mm2 price for "+coin)
        kmd_orders = rpclib.orderbook(node_ip, user_pass, coin, 'KMD').json()
        kmd_value = 0
        min_kmd_value = 999999999999999999
        total_kmd_value = 0
        max_kmd_value = 0
        kmd_volume = 0
        num_asks = len(kmd_orders['asks'])
        for asks in kmd_orders['asks']:
            kmd_value = float(asks['maxvolume']) * float(asks['price'])
            if kmd_value < min_kmd_value:
                min_kmd_value = kmd_value
            elif kmd_value > max_kmd_value:
                max_kmd_value = kmd_value
            total_kmd_value += kmd_value
            kmd_volume += float(asks['maxvolume'])
        if num_asks > 0:
            median_kmd_value = total_kmd_value/kmd_volume
        else:
            min_kmd_value = 'No Data'
            median_kmd_value = 'No Data'
            max_kmd_value = 'No Data'
        return min_kmd_value, median_kmd_value, max_kmd_value
    except:
        min_kmd_value = 'No Data'
        median_kmd_value = 'No Data'
        max_kmd_value = 'No Data'
        return min_kmd_value, median_kmd_value, max_kmd_value


def get_trade_price_val(creds, base, rel, balance):
    base_btc_price = get_btc_price(creds[5], base)
    rel_btc_price = get_btc_price(creds[5], rel)
    rel_price = base_btc_price/rel_btc_price
    trade_price = rel_price+rel_price*float(creds[7])/100
    trade_val = round(float(rel_price)*float(balance),8)
    return trade_price, trade_val


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

# TODO: parse https://api.coinpaprika.com/v1/coins for supported coins api-codes
def get_paprika_price(coin_id):
    #print("getting paprika api prices")
    url = 'https://api.coinpaprika.com/v1/ticker/'+coin_id
    r = requests.get(url)
    return r

def prices_loop():
    print("starting prices loop")
    prices_data = {
        "binance":{

        },
        "paprika":{

        },
        "gecko":{

        },
        "average":{

        }
    }
    binance_data = requests.get("https://api.binance.com/api/v1/ticker/allPrices").json()
    binance_prices = {}
    for item in binance_data:
        binance_prices.update({item['symbol']:item['price']})
    for quoteAsset in binance_api.quoteAssets:
        prices_data['binance'][quoteAsset] = {}
        for baseAsset in binance_api.base_asset_info:
            if baseAsset in coinslib.cointags:
                if baseAsset not in prices_data['binance']:
                    prices_data['binance'][baseAsset] = {}
                if baseAsset+quoteAsset in binance_prices:
                    price = float(binance_prices[baseAsset+quoteAsset])
                    invert_price = 1/price
                    prices_data['binance'][quoteAsset].update({baseAsset:price})
                    prices_data['binance'][baseAsset].update({quoteAsset:price})

    paprika_data = requests.get("https://api.coinpaprika.com/v1/tickers?quotes=USD%2CBTC").json()
    for item in paprika_data:
        if item['symbol'] in coinslib.cointags:
            prices_data['paprika'].update({
                item['symbol']:{
                    "USD":item['quotes']['USD']['price'],
                    "BTC":item['quotes']['BTC']['price'],
                }
            })

    gecko_data = gecko_prices(",".join(coinslib.gecko_ids), 'usd,btc').json()
    for coin in coinslib.cointags:
        api_sum_usd = 0
        api_sum_btc = 0
        api_sources = []
        if coinslib.coin_api_codes[coin]['coingecko_id'] != '':
            prices_data['gecko'].update({
                coin:{
                    "USD":gecko_data[coinslib.coin_api_codes[coin]['coingecko_id']]['usd'],
                    "BTC":gecko_data[coinslib.coin_api_codes[coin]['coingecko_id']]['btc'],
                }
            })
            api_sum_usd += prices_data['gecko'][coin]['USD']
            api_sum_btc += prices_data['gecko'][coin]['BTC']
            api_sources.append('CoinGecko')
        if coin in prices_data['paprika']:
            api_sum_usd += prices_data['paprika'][coin]['USD']
            api_sum_btc += prices_data['paprika'][coin]['BTC']
            api_sources.append('CoinPaprika')
        if coin in prices_data['binance']:
            if 'TUSD' in prices_data['binance'][coin]:
                api_sum_usd += prices_data['binance'][coin]['TUSD']
            if coin == 'BTC':
                api_sum_btc += 1
            else:
                api_sum_btc += 1/prices_data['binance']['BTC'][coin]
            api_sources.append('Binance')
            
        if len(api_sources) > 0:
            prices_data['average'].update({
                coin:{
                    "USD":api_sum_usd/len(api_sources),
                    "BTC":api_sum_btc/len(api_sources),
                    "sources":api_sources
                }
            })
        else:
            prices_data['average'].update({
                coin:{
                    "USD":'No Data',
                    "BTC":'No Data',
                    "sources":api_sources
                }
            })
    print("prices loop completed")
    return prices_data