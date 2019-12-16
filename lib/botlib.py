#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from . import rpclib, priceslib, binance_api

def start_mm2_bot_loop(creds, buy_coins, sell_coins, cancel_previous, trade_max):
    for base in sell_coins:
        for rel in buy_coins:
            if base != rel:
                pass
                    # detect unfinished swaps


def cancel_session_orders(session):
    print("cancelling session orders")
    if 'binance' in session['cex_open_orders']:
        binance_orders = session['cex_open_orders']['binance']
        for symbol in binance_orders:
            order_id = binance_orders[symbol]
            binance_api.delete_order(bn_key, bn_secret, symbol, order_id)
    # add other cex when integrated
    mm2_order_uuids = session['mm2_open_orders']
    for order_uuid in mm2_order_uuids:
        rpclib.cancel_uuid(mm2_ip, mm2_rpc_pass, order_uuid)

def submit_strategy_orders(mm2_ip, mm2_rpc_pass, strategy):
    prices_data = priceslib.prices_loop()
    print("submitting strategy orders")
    print("Strategy: "+str(strategy))
    base_list = strategy['base_list']
    rel_list = strategy['rel_list']
    margin = strategy['margin']
    balance_pct = strategy['balance_pct']
    if strategy['strategy_type'] == 'margin':
        for base in base_list:
            for rel in rel_list:
                if base != rel:
                    # in case prices data not yet populated
                    if base in prices_data['average']:
                        base_btc_price = prices_data['average'][base]['BTC']
                        rel_btc_price = prices_data['average'][rel]['BTC']
                        # todo: make fin safe (no float)
                        rel_price = (base_btc_price/rel_btc_price)*(1+margin/100)
                        base_balance_info = rpclib.my_balance(mm2_ip, mm2_rpc_pass, base).json()
                        available_base_balance = float(base_balance_info["balance"]) - float(base_balance_info["locked_by_swaps"])
                        basevolume = available_base_balance * strategy['balance_pct']/100
                        print("trade price: "+base+" (base) / "+rel+" (rel) "+str(rel_price)+" volume = "+str(basevolume))
                        # place new order TODO: check if swap in progress.
                        if strategy['balance_pct'] != 100:
                            resp = rpclib.setprice(mm2_ip, mm2_rpc_pass, base, rel, basevolume, rel_price, False, True)
                        else:
                            resp = rpclib.setprice(mm2_ip, mm2_rpc_pass, base, rel, basevolume, rel_price, True, True)
                        print("rpclib.setprice("+mm2_ip+", "+mm2_rpc_pass+", "+base+", "+str(rel)+", "+str(rel_price))
                        print(resp.json())
                    else:
                        print("No price data yet...")
                        return
    elif strategy['strategy_type'] == 'arbitrage':
        run_arb_strategy(mm2_ip, mm2_rpc_pass, strategy)


def bot_loop(mm2_ip, mm2_rpc_pass, prices_data):
    print("starting bot loop")
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    bot_data = "bot data placeholder"
    for strategy_name in strategies:
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        if history['status'] == 'active':
            print("Active strategy: "+strategy_name)
            with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
                strategy = json.loads(f.read())
            # check refresh interval vs last refresh
            print("last_refresh: "+str(history['last_refresh']))
            print("refresh_interval: "+str(strategy['refresh_interval']*2))
            print("last + refresh_interval: "+str(strategy['refresh_interval']*2+history['last_refresh']))
            print(str(strategy['refresh_interval']*2+history['last_refresh'])+" < "+str(int(time.time())))
            print("now: "+str(int(time.time())))
            if history['last_refresh'] == 0 or history['last_refresh'] + strategy['refresh_interval']*2 < int(time.time()):
                print("*** Refreshing strategy: "+strategy_name+" ***")
                history.update({'last_refresh':int(time.time())})
                session = history['sessions'][str(len(history['sessions'])-1)]
                # cancel old orders
                cancel_session_orders(session)
                # place fresh orders
                submit_strategy_orders(mm2_ip, mm2_rpc_pass, strategy)
                # update session history
                with open(sys.path[0]+"/history/"+strategy_name+".json", 'w+') as f:
                     f.write(json.dumps(history))
    print("bot loop completed")
    return bot_data

def orderbook_loop(mm2_ip, mm2_rpc_pass, ):
    print("starting orderbook loop")
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    active_coins = []
    for strategy_name in strategies:
        with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
            strategy = json.loads(f.read())
            active_coins += strategy['rel_list']
            active_coins += strategy['base_list']
    active_coins = list(set(active_coins))
    orderbook_data = []
    for base in active_coins:
        for rel in active_coins:
            if base != rel:
                orderbook_pair = get_mm2_pair_orderbook(mm2_ip, mm2_rpc_pass, base, rel)
                orderbook_data.append(orderbook_pair)
    print("orderbook loop completed")
    return orderbook_data

def get_mm2_pair_orderbook(mm2_ip, mm2_rpc_pass, base, rel):
    orderbook = rpclib.orderbook(mm2_ip, mm2_rpc_pass, base, rel).json()
    asks = []
    bids = []
    for order in orderbook['asks']:
        ask = {
                "base": base,
                "rel": rel,
                "price": order['price'],
                "max_volume":order['maxvolume'],
                "age":order['age']
        }
        asks.append(ask)
    for order in orderbook['bids']:
        bid = {
                "base": base,
                "rel": rel,
                "price": order['price'],
                "max_volume":order['maxvolume'],
                "age":order['age']
        }
        bids.append(bid)
    orderbook_pair = {
        base+rel: {
            "asks":asks,
            "bids":bids
        }
    }
    return orderbook_pair


def balances_loop(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, prices_data):
    print("starting balances loop")
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    active_coins = rpclib.check_active_coins(mm2_ip, mm2_rpc_pass)
    quoteassets = []
    for strategy_name in strategies:
        with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
            strategy = json.loads(f.read())
            active_coins += strategy['rel_list']
            active_coins += strategy['base_list']
    active_coins = list(set(active_coins))

    balances_data = {
        "mm2": {},
        "binance": {},
        "binance_quote_assets": {}
    }
    binance_balances = binance_api.get_binance_balances(bn_key, bn_secret)
    for coin in active_coins:
        # get binance balance
        if coin in binance_balances:
            available = binance_balances[coin]['available']
            balances_data["binance"].update({coin:available})
        # get mm2 balance        
        balance_info = rpclib.my_balance(mm2_ip, mm2_rpc_pass, coin).json()
        balance = balance_info['balance']
        locked = balance_info['locked_by_swaps']
        available = float(balance) - float(locked)
        balances_data["mm2"].update({coin:available})
        if coin in prices_data['binance']:
            quoteassets += list(prices_data['binance'][coin].keys())
    quoteassets = list(set(quoteassets))
    for coin in quoteassets:
        if coin in prices_data['binance'] and coin not in balances_data and coin in binance_balances:
            available = binance_balances[coin]['available']
            balances_data["binance_quote_assets"].update({coin:available})
    print("balances loop completed")
    return balances_data
    # TODO: test this with API keys active

## Use orderbook and prices data to identigy aritrage opportunities

def run_arb_strategy(mm2_ip, mm2_rpc_pass, strategy):
    orderbook_data = orderbook_loop(mm2_ip, mm2_rpc_pass)
    prices_data = priceslib.prices_loop()
    # check balances
    balances = {}
    for base in strategy['base_list']:
        for rel in strategy['rel_list']:
            if base != rel:
                # get binance price
                binance_prices = priceslib.get_binance_price(base, rel, prices_data)
                if 'direct' in binance_prices:
                    print("Binance Price (direct): "+str(binance_prices['direct']))
                if 'indirect' in binance_prices:
                    for quote in binance_prices['indirect']:
                        print("Binance Price (indirect via "+quote+"): "+str(binance_prices['indirect'][quote]))
                print("mm2 offers: "+base+rel)
                for pair in orderbook_data:
                    if base+rel in pair:
                        bids = pair[base+rel]['asks']
                        asks = pair[base+rel]['bids']
                print("BIDS")
                for item in bids:
                    print(item)
                print("ASKS")
                for item in asks:
                    print(item)
                print("---------------------------------------------------------")
            # check if any mm2 orders under binance price
            pass

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
    return history

def init_history_file(name, strategy_coins):
    balance_deltas = {}
    for strategy_coin in strategy_coins:
        balance_deltas.update({strategy_coin:0})
    history = { 
        "num_sessions":0,
        "sessions":{},
        "last_refresh": 0,
        "total_mm2_swaps_completed": 0,
        "total_cex_swaps_completed": 0,
        "total_balance_deltas": balance_deltas,
        "status":"inactive"
    }
    with open("history/"+name+".json", 'w+') as f:
        f.write(json.dumps(history))

def init_strategy_file(name, strategy_type, rel_list, base_list, margin, refresh_interval, balance_pct, cex_list):
    strategy = {
        "name":name,
        "strategy_type":strategy_type,
        "rel_list":rel_list,
        "base_list":base_list,
        "margin":margin,
        "refresh_interval":refresh_interval,
        "balance_pct":balance_pct,
        "cex_countertrade":cex_list
    }
    with open("strategies/"+name+'.json', 'w+') as f:
        f.write(json.dumps(strategy))

    if not os.path.exists(sys.path[0]+"/history/"+name+".json"):
        strategy_coins = list(set(rel_list+base_list))
        init_history_file(name, strategy_coins)
    return strategy

def init_session(strategy_name, strategy, history):
    history.update({"status":"active"})
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
    with open("history/"+strategy_name+".json", 'w+') as f:
        f.write(json.dumps(history))
    with open("strategies/"+strategy_name+".json", 'w+') as f:
        f.write(json.dumps(strategy))