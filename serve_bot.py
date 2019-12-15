#!/usr/bin/env python3
from typing import Optional, List
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from starlette.status import HTTP_401_UNAUTHORIZED
from threading import Thread
import asyncio
import logging
#import sqlite3
from lib import rpclib, botlib, coinslib, priceslib, validatelib
import time
import json
import sys
import os

# what does bot do when mm2 is down? Respawn, or exit (could leave open orders)?


## ALTERNATIVE APIS
### DEX: https://api.blocknet.co/#xbridge-api / https://github.com/blocknetdx/dxmakerbot requires syncd local nodes

# todo: detect Ctrl-C or bot exit/death, then cancel all orders. blocking thread might allow this?
# in thread, check strategies. for active strategies, last refresh time, and refresh interval. If time to refresh, refresh.

## JSON Schemas
    

'''
    path = ./strategies/{strategy_name}.json

    strategy = {
        "name": str,
        "strategy_type": str,
        "rel_list": list,
        "base_list": list,
        "margin": float,
        "refresh_interval": int,
        "balance_pct": int,
        "cex_countertrade": list,
        "reference_api": str
    }
'''


'''
    path = ./history/{strategy_name}.json

    history = { 
        "num_sessions": dict,
        "sessions":{
            "1":{
                "started": timestamp,
                "duration": int,
                "mm2_open_orders": list,
                "mm2_swaps_in_progress": dict,
                "mm2_swaps_completed": dict,
                "cex_open_orders": dict,
                "cex_swaps_in_progress": dict,
                "cex_swaps_completed": dict,
                "balance_deltas": dict,
            }
        },
        "last_refresh": int,
        "total_mm2_swaps_completed": int,
        "total_cex_swaps_completed": int,
        "total_balance_deltas": dict,
        "status":str
    }
'''

'''
    cached in mem

    prices = {
        coingecko:{},
        coinpaprika:{},
        binance:{},
        average:{}
    }
'''

rpc_url = "http://127.0.0.1:7783"
config_folders = ['strategies', 'history']

for folder in config_folders:
    if not os.path.exists(folder):
        os.makedirs(folder)
bot_data = {}
orderbook_data = {}
balances_data = {}
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

def colorize(string, color):
    colors = {
        'black':'\033[30m',
        'red':'\033[31m',
        'green':'\033[32m',
        'orange':'\033[33m',
        'blue':'\033[34m',
        'purple':'\033[35m',
        'cyan':'\033[36m',
        'lightgrey':'\033[37m',
        'darkgrey':'\033[90m',
        'lightred':'\033[91m',
        'lightgreen':'\033[92m',
        'yellow':'\033[93m',
        'lightblue':'\033[94m',
        'pink':'\033[95m',
        'lightcyan':'\033[96m',
    }
    if color not in colors:
        return str(string)
    else:
        return colors[color] + str(string) + '\033[0m'

creds_json_file = 'creds.json'
if not os.path.exists(creds_json_file):
    with open(creds_json_file, 'w') as f:
        creds = {
            "mm2_rpc_pass": "",
            "mm2_ip": "http://127.0.0.1:7783",
            "bn_key": "",
            "bn_secret": "",
        }
        f.write(json.dumps(creds))

with open(creds_json_file) as j:
    try:
        creds_json = json.load(j)
        if 'mm2_rpc_pass' in creds_json:
            mm2_rpc_pass = creds_json['mm2_rpc_pass']
        if 'mm2_ip' in creds_json:
            mm2_ip = creds_json['mm2_ip']
        if 'bn_key' in creds_json:
            bn_key = creds_json['bn_key']
        if 'bn_secret' in creds_json:
            bn_secret = creds_json['bn_secret']
    except Exception as e:
        print(colorize("getting creds failed", 'red'))
        print(e)

if mm2_rpc_pass == '':
    print(colorize("ERROR: You need to put your mm2 'mm2_rpc_pass' into creds.json to interact with Antara MarketMaker!", 'red'))
    print(colorize("ERROR: It should match the rpc_pass in your MM2.json file", 'red'))
    print(colorize("ERROR: Use Control-C to exit...", 'red'))

if bn_key == '' or bn_secret == '':
    print(colorize("WARNING: If you want to use Binance functionality, you need to put your API keys into creds.json", 'orange'))

### THREAD Classes

class price_update_thread(object):
    def __init__(self, interval=60):
        self.interval = interval
        thread = Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        global prices_data
        while True:
            prices_data = priceslib.prices_loop()
            time.sleep(self.interval)

prices_thread = price_update_thread()

class bot_update_thread(object):
    def __init__(self, interval=90):                  # 20 min, TODO: change to var
        self.interval = interval
        thread = Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        while True:
            global bot_data
            bot_data = botlib.bot_loop(mm2_ip, mm2_rpc_pass, prices_data)
            time.sleep(self.interval)

bot_thread = bot_update_thread()

class orderbook_update_thread(object):
    def __init__(self, interval=10):                  # 20 min, TODO: change to var
        self.interval = interval
        thread = Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        while True:
            global orderbook_data
            orderbook_data = botlib.orderbook_loop(mm2_ip, mm2_rpc_pass)
            time.sleep(self.interval)

orderbook_thread = orderbook_update_thread()

class balances_update_thread(object):
    def __init__(self, interval=60):                  # 20 min, TODO: change to var
        self.interval = interval
        thread = Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        while True:
            global balance_data
            balance_data = botlib.balances_loop(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, prices_data)
            time.sleep(self.interval)

balance_thread = balances_update_thread()

### API CALLS

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to Antara Markerbot API. See /docs for all methods"}

@app.get("/all_balances")
async def all_balances():
    """
    Returns MM2 and CEX balances
    """
    global balance_data
    return balance_data

@app.post("/strategies/create")
async def create_strategy(*, name: str, strategy_type: str, rel_list: str, 
                          base_list: str, margin: float = 5, refresh_interval: int = 30,
                          balance_pct: int = 100, cex_list: str = 'binance'):
    """
    Creates a new trading strategy definition.
    - **name**: Each strategy must have a name. E.g. KMD
    - **strategy_type**: A valid strategy name. E.g. Margin
    - **rel_list**: a comma delimited list of tickers. E.g. KMD,BTC,ETH
    - **base_list**: a comma delimited list of tickers. E.g. KMD,BTC,ETH
    - **margin** (float): percentage to set sell orders above market (margin), or buy orders below market (arbitrage). E.g. 5 
    - **refresh_interval** (integer): time in minutes between refreshing prices and updating orders.
    - **balance_pct** (integer): percentage of available balance to use for trades. E.g. 100
    - **base_list**: a comma delimited list of centralised exchanges. E.g. Binance,Coinbase

    """
    valid_strategies = ['margin', 'arbitrage']
    if name == 'all':
        resp = {
            "response": "error",
            "message": "Strategy name 'all' is reserved, use a different name.",
        }
    elif strategy_type in valid_strategies:
        rel_list = rel_list.split(',')
        base_list = base_list.split(',')
        cex_list = cex_list.split(',')
        valid_coins = validatelib.validate_coins(list(set(rel_list+base_list)))
        valid_cex = validatelib.validate_cex(list(set(cex_list)))
        if not valid_coins[0]:
            resp = {
                "response": "error",
                "message": "'"+valid_coins[1]+"' is an invalid ticker. Check /coins/list for valid options, and enter them as comma delimiter with no spaces."
            }
            return resp
        if not valid_cex[0]:
            resp = {
                "response": "error",
                "message": "'"+valid_cex[1]+"' is an invalid CEX. Check /cex/list for valid options, and enter them as comma delimiter with no spaces."
            }
            return resp
        strategy = botlib.init_strategy_file(name, strategy_type, rel_list, base_list, margin, refresh_interval, balance_pct, cex_list)
        resp = {
            "response": "success",
            "message": "Strategy '"+name+"' created",
            "parameters": strategy
        }
    else:
        resp = {
            "response": "error",
            "message": "Strategy type '"+strategy_type+"' is invalid. Options are: "+str(valid_strategies),
            "valid_strategies": {
                "margin": "This strategy will place setprice (sell) orders on mm2 at market price plus margin. On completion of a swap, if Binance keys are valid, a countertrade will be performed at market.",
                "arbitrage": "This strategy scans the mm2 orderbook periodically. If a trade below market price minus margin is detected, a buy order is submitted. On completion of a swap, if Binance keys are valid, a counter sell will be submitted."
            }
        }
    return resp

@app.get("/coins/list")
async def list_coins():
    resp = {
        "response": "success",
        "message": "Coins list found",
        "coins_list": coinslib.cointags
    }
    return resp

@app.get("/cex/list")
async def list_cex():
    resp = {
        "response": "success",
        "message": "Cex list found",
        "cex_list": coinslib.cex_names
    }
    return resp

@app.get("/orderbook")
async def show_orderbook():
    resp = {
        "response": "success",
        "orderbook": orderbook_data
    }        
    return resp


@app.post("/binance_prices/{base}/{rel}")
async def coin_prices(base, rel):
    base = base.upper()
    rel = rel.upper()
    prices = priceslib.get_binance_price(base, rel, prices_data)
    resp = {
        "response": "success",
        "message": base+"/"+rel+" price data found",
        "binance_prices": prices
    }
    
    return prices

@app.get("/prices/{coin}")
async def coin_prices(coin):
    coin = coin.upper()
    if coin == 'ALL':

        resp = {
            "response": "success",
            "message": coin+" price data found",
            "price_data": prices_data,
        }
    elif coin in prices_data['average']:
        coin_price_data = {
            "binance":{coin:prices_data['binance'][coin]},
            "paprika":{coin:prices_data['paprika'][coin]},
            "gecko":{coin:prices_data['gecko'][coin]},
            "average":{coin:prices_data['average'][coin]}
        }
        resp = {
            "response": "success",
            "message": coin+" price data found",
            "price_data": coin_price_data,
        }
    else:
        resp = {
            "response": "error",
            "message": coin+" price data not found!"
        }        
    return resp

@app.get("/strategies/list")
async def list_strategies():
    json_files = [ x for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    strategies = []
    for json_file in json_files:
        with open(sys.path[0]+'/strategies/'+json_file) as j:
            strategy = json.loads(j.read())
            strategies.append(strategy)
    return strategies

@app.get("/strategies/active")
async def active_strategies():
    json_files = [ x for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    count = 0
    strategies = []
    for json_file in json_files:
        with open(sys.path[0]+'/history/'+json_file) as j:
            history = json.loads(j.read())
        if history["status"] == 'active':
            with open(sys.path[0]+'/strategies/'+json_file) as j:
                strategy = json.loads(j.read())
            count += 1
            strategies.append(strategy)
    resp = {
        "response": "success",
        "message": str(count)+" strategies active",
        "active_strategies": strategies
    }
    return resp

@app.post("/strategies/history/{strategy_name}")
async def strategy_history(strategy_name):
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    if len(strategies) == 0:
        resp = {
            "response": "error",
            "message": "No strategies found!"
        }
    elif strategy_name == 'all':
        histories = []
        for strategy in strategies:
            with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
                history = json.loads(f.read())
            histories.append(history)
        resp = {
            "response": "success",
            "message": str(len(strategies))+" found!",
            "histories": histories
        }
    elif strategy_name not in strategies:
        resp = {
            "response": "error",
            "message": "Strategy '"+strategy_name+"' not found!"
        }
    else:
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        resp = {
            "response": "success",
            "message": "History found for strategy: "+strategy_name,
            "history": history
        }
    print(bot_data)
    return resp

@app.post("/strategies/run/{strategy_name}")
async def run_strategy(strategy_name):
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    print(strategies)
    if strategy_name in strategies:
        with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
            strategy = json.loads(f.read())
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        if strategy['strategy_type'] == "margin":
            botlib.init_session(strategy_name, strategy, history)
            resp = {
                "response": "success",
                "message": "Strategy '"+strategy['name']+"' started!",
            }
        elif strategy['strategy_type'] == "arbitrage":
            botlib.init_session(strategy_name, strategy, history)
            resp = {
                "response": "success",
                "message": "Strategy '"+strategy['name']+"' started",
            }
        else:
            resp = {
                "response": "error",
                "message": "Strategy type '"+strategy['strategy_type']+"' not recognised!"
            }
    else:
        resp = {
            "response": "error",
            "message": "Strategy '"+strategy['name']+"' not found!"
        }
    return resp


@app.post("/strategies/stop/{strategy_name}")
async def stop_strategy(strategy_name):
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    if strategy_name == 'all':
        histories = []
        for strategy in strategies:
            with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
                history = json.loads(f.read())
            if history['status'] == 'active':
                history.update({"status":"inactive"})
                history = botlib.cancel_strategy(history)
                with open(sys.path[0]+"/history/"+strategy_name+".json", 'w+') as f:
                    f.write(json.dumps(history))
                histories.append(history)
        resp = {
            "response": "success",
            "message": "All active strategies stopped!",
            "status": histories
        }        
    elif strategy_name not in strategies:
        resp = {
            "response": "error",
            "message": "Strategy '"+strategy_name+"' not found!"
        }
    else:
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        history.update({"status":"inactive"})

        with open(sys.path[0]+"/history/"+strategy_name+".json", 'w+') as f:
            f.write(json.dumps(history))
        resp = {
            "response": "success",
            "message": "Strategy '"+strategy_name+"' stopped",
            "status": history
        }
    return resp



def main():
   # bot_thread = threading.Thread(target=bot_loop, args=())
   # prices_thread = threading.Thread(target=prices_loop, args=())
   pass

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
'''
method: start_trade strategy: marketmaking``margin: 10 tickers_base: [BTC, KMD] tickers_rel: [VRSC]
method: get_trading_status -> result: success list_of_strategies_working: [1,2,3]


stop_strategy strategy_id -> result
started_strategies_list -> list_with_ids 
history_strategies_list -> displaying `active` and `history` (stopped) of strategies
strategy_info strategy_id -> info with params and some events maybe (at least amount of events)
strategy_events strategy_id <depth> -> displaying events (trades/transfers and etc) for strategy with optional depth (amount of last events to show) argument
'''

# strategies examples - https://github.com/CoinAlpha/hummingbot/tree/master/documentation/docs/strategies

## API methods

# start_trading(rel_list, base_list, margin, refresh_interval=30 (optional, minutes), balance_pct=100 (optional, default 100), cex_countertrade=None (optional, cex_name or None).
# if cex not None, check if cex_auth is ok.
# if refresh interval expires while swap in progress, wait before cancel.
# monitor trade status periodically, emit on updates. 
# emits bot history json - see mmbot_qt for format. if json contains initiated swaps, after finish/ order cancel, store locally on client.

# get_strategy_status(strategy_id, verbose=False)
# forces update and emit of bot history json for id. Return enough to get more info from mm2 if verbose=True.

# get_completed_trades_history(limit=10, from='', verbose=False)
# returns bot history json for last "limit" trades. Augment via mm2 for more data if verbose=True

# show_strategy(strategy_id)
# returns strategy_input_params, pending_trade_ids, completed_trade_ids, aggregated_balance_deltas

# stop_trading(strategy_id, force=False)
# check for in progress cex/mm2 trades. Cancel if None. If not None, schedule for cancel once in progress tradess complete.
# If force is true, cancel regardless.

# get_active_strategies()
# show list of strategies currently in progress.

# arbitrage(cex_list, coin_pair, min_profit_pct)
# for a given coin_pair (e.g. KMDBTC), monitor all cex on the list, and mm2 for prices. If price differential between exchanges exceeds min_profit_pct, execute matching trades to take advantage.
