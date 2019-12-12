#!/usr/bin/env python3
from typing import Optional, List
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from starlette.status import HTTP_401_UNAUTHORIZED
import threading
import logging
#import sqlite3
import rpclib
import time
import json
import sys
import os


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

### THREAD FUNCTIONS

def prices_loop():
    # periodically refresh prices and cache for reference.
    pass

def bot_loop():
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    for strategy in strategies:
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        if history['status'] == 'active':
            with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
                strategy = json.loads(f.read())

            # check refresh interval vs last refresh
            if history['last_refresh'] + strategy['refresh_interval']*60 > int(time.time()):
                session = history['sessions'][str(len(sessions)-1)]

                # cancel_orders
                binance_orders = session['cex_open_orders']['binance']
                for symbol in binance_orders:
                    order_id = binance_orders[symbol]
                    binance_api.delete_order(bn_key, bn_secret, symbol, order_id)
                mm2_order_uuids = session_history['mm2_open_orders']
                for order_uuid in mm2_order_uuids:
                    rpclib.cancel_uuid(mm2_ip, mm2_rpc_pass, order_uuid)

                # place fresh orders
                base_list = strategy['base_list']
                rel_list = strategy['rel_list']
                margin = strategy['margin']
                balance_pct = strategy['balance_pct']
                if strategy['strategy_type'] == 'margin':
                    for base in base_list:
                        for rel in rel_list:
                            if base != rel:
                                # get trade price from api + margin
                                # place new order
                                pass



            history['status']

            history.update({})
        "name": str,
        "strategy_type": str,
        "rel_list": list,
        "base_list": list,
        "margin": float,
        "refresh_interval": int,
        "balance_pct": int,
        "cex_countertrade": list

            history = cancel_strategy(history)
            with open(sys.path[0]+"/history/"+strategy_name+".json", 'w+') as f:
                f.write(json.dumps(history))


### BOT LOGIC FUNCTIONS

def margin_strategy_cancel(uuid_list):


### API CALLS

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to Antara Markerbot API. See /docs for all methods"}

@app.post("/balance/{coin}")
async def get_balance(coin: str = Field(None, description='Enter Coin Ticker', max_length=6)):
    balance_info = rpclib.my_balance(mm2_ip, mm2_rpc_pass, coin).json()
    return balance_info

# TODO: add domain validation for cex, tickers, strat_types
@app.post("/strategies/create")
async def create_strategy(name: str,
                          strategy_type: str,
                          rel_list: List[str], 
                          base_list: List[str],
                          margin: float = 5,
                          refresh_interval: int = 30,
                          balance_pct: int = 100,
                          cex_countertrade: List[str] = []):
    if name == 'all':
        resp = {
            "response": "error",
            "message": "Strategy name 'all' is reserved, use a different name.",
        }
    else:
        strat_file = name+'.json'
        strategy = {
            "name":name,
            "strategy_type":strategy_type,
            "rel_list":rel_list,
            "base_list":base_list,
            "margin":margin,
            "refresh_interval":refresh_interval,
            "balance_pct":balance_pct,
            "cex_countertrade":cex_countertrade
        }
        with open("strategies/"+strat_file, 'w+') as f:
            f.write(json.dumps(strategy))
        resp = {
            "response": "success",
            "message": "Strategy '"+name+"' created",
            "parameters": strategy
        }
    return resp

@app.post("/strategies/list")
async def list_strategies():
    json_files = [ x for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    strategies = []
    for json_file in json_files:
        with open(sys.path[0]+'/strategies/'+json_file) as j:
            strategy = json.loads(j.read())
            strategies.append(strategy)
    return strategies

@app.post("/strategies/active")
async def active_strategies():
    json_files = [ x for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    count = 0
    strategies = []
    for json_file in json_files:
        with open(sys.path[0]+'/strategies/'+json_file) as j:
            strategy = json.loads(j.read())
            if strategy["status"] == 'active':
                count += 1
                strategies.append(strategy)
    resp = {
        "response": "success",
        "message": str(count)+" strategies active",
        "active_strategies": strategies
    }
    return resp

def cancel_strategy(history):
    session = history['sessions'][str(len(history['sessions']))]
    started_at = session['started']
    duration = int(time.time()) - started_at
    session.update({"duration":duration})

    mm2_open_orders = session["mm2_open_orders"]
    for order_uuid in mm2_open_orders:
        rpclib.cancel_uuid(mm2_ip, mm2_rpc_pass, order_uuid)
    cex_open_orders = session["cex_open_orders"]
    for order in cex_open_orders:
        if 'binance' in cex_open_orders:
            for symbol in cex_open_orders['binance']:
                order_id = cex_open_orders['binance'][symbol]
                binance_api.delete_order(bn_key, bn_secret, symbol, order_id)

    mm2_swaps_in_progress = session["mm2_swaps_in_progress"]
    for swap in mm2_swaps_in_progress:
        # alreay cancelled, move to completed, and mark as "cancelled while in progress"
        pass
    cex_swaps_in_progress = session["cex_swaps_in_progress"]
    for swap in cex_swaps_in_progress:
        # alreay cancelled, move to completed, and mark as "cancelled while in progress"
        pass

    balance_delta_coins = list(session["balance_deltas"].keys())
    mm2_swaps_completed = session["mm2_swaps_completed"]
    for swap in mm2_swaps_completed:
        # calculate deltas
        pass
    cex_swaps_completed = session["cex_swaps_completed"]
    for swap in cex_swaps_completed:
        # calculate deltas
        pass

    session.update({"balance_deltas":balance_deltas})
    sessions.update({str(len(history['sessions'])):session})
    history.update({"sessions":sessions})

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
                history = cancel_strategy(history)
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
            "message": strategy_name+" stopped",
            "status": history
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
    elif not os.path.exists(sys.path[0]+"/history/"+strategy_name+".json"):
        history = { 
            "num_sessions":{},
            "sessions":{},
            "last_refresh": 0,
            "total_mm2_swaps_completed": {},
            "total_cex_swaps_completed": {},
            "total_balance_deltas": {},
            "status":"inactive"
        }
        resp = {
            "response": "success",
            "message": "History found for strategy: "+strategy_name,
            "history": history
        }        
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'w+') as f:
            f.write(json.dumps(resp))
    else:
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            resp = json.loads(f.read())
    return resp

@app.post("/strategies/run/{strategy_name}")
async def run_strategy(strategy_name):
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    if strategy_name in strategies:
        with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
            strategy = json.loads(f.read())
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        if strategy['type'] == "margin":
            #result = botlib.run_margin_strategy(strategy)
            strategy.update({"status":"active"})
            # init balance datas
            balance_deltas = {}
            for rel in strategy["rel_list"]:
                balance_deltas.update({rel:0})
            for base in strategy["base_list"]:
                if base not in strategy["rel_list"]:
                    balance_deltas.update({base:0})
            # init session
            sessions = history['sessions']
            sessions.update({str(len(sessions)):{
                    "started":int(time.time()),
                    "duration":0,
                    "mm2_open_orders": {},
                    "mm2_swaps_in_progress": {},
                    "mm2_swaps_completed": {},
                    "cex_open_orders": {},
                    "cex_swaps_in_progress": {},
                    "cex_swaps_completed": {},
                    "balance_deltas": balance_deltas,
                }})
            history.update({"sessions":sessions})
            with open("history/"+strategy_name, 'w+') as f:
                f.write(json.dumps(history))
            with open("strategies/"+strategy_name, 'w+') as f:
                f.write(json.dumps(strategy))
            resp = {
                "response": "success",
                "message": "Strategy '"+strategy['type']+"' started!",
            }
            pass
        elif strategy['type'] == "arbritage":
            #result = botlib.run_arb_strategy(strategy) TO THREAD
            strategy.update({"status":"active"})
            # init balance datas
            balance_deltas = {}
            for rel in strategy["rel_list"]:
                balance_deltas.update({rel:0})
            for base in strategy["base_list"]:
                if base not in strategy["rel_list"]:
                    balance_deltas.update({base:0})
            # init session
            sessions = history['sessions']
            sessions.update({str(len(sessions)):{
                    "started":int(time.time()),
                    "duration":0,
                    "mm2_open_orders": {},
                    "mm2_swaps_in_progress": {},
                    "mm2_swaps_completed": {},
                    "cex_open_orders": {},
                    "cex_swaps_in_progress": {},
                    "cex_swaps_completed": {},
                    "balance_deltas": balance_deltas,
                }})
            history.update({"sessions":sessions})
            with open("history/"+strategy_name, 'w+') as f:
                f.write(json.dumps(history))
            with open("strategies/"+strategy_name, 'w+') as f:
                f.write(json.dumps(strategy))
            resp = {
                "response": "success",
                "message": "Strategy '"+strategy['type']+"' started",
            }
            pass
        else:
            resp = {
                "response": "error",
                "message": "Strategy '"+strategy['type']+"' not found!"
            }
    else:
        resp = {
            "response": "error",
            "message": "Strategy '"+strategy_name+"' not found!"
        }
    return resp


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    bot_thread = threading.Thread(target=bot_loop, args=())
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
