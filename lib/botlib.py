#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from . import rpclib   

def start_mm2_bot_loop(creds, buy_coins, sell_coins, cancel_previous, trade_max):
    for base in sell_coins:
        for rel in buy_coins:
            if base != rel:
                pass
                    # detect unfinished swaps

def run_margin_strategy(strategy):
    while True:

        strategy['refresh_interval']

    pass

def run_arb_strategy(strategy):

    pass

    {
        "name":name,
        "strategy_type":strategy_type,
        "rel_list":rel_list,
        "base_list":base_list,
        "margin":margin,
        "refresh_interval":refresh_interval,
        "balance_pct":balance_pct,
        "cex_countertrade":cex_countertrade
    }

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

def submit_strategy_orders(strategy, prices_data):
    print("submitting strategy orders")
    print("Strategy: "+str(strategy))
    base_list = strategy['base_list']
    rel_list = strategy['rel_list']
    margin = strategy['margin']
    balance_pct = strategy['balance_pct']
    print("strat: "+str(strategy))
    if strategy['strategy_type'] == 'margin':
        for base in base_list:
            for rel in rel_list:
                if base != rel:
                    # in case prices data not yet populated
                    if base in prices_data['average']:
                        base_btc_price = prices_data['average'][base]
                        rel_btc_price = prices_data['average'][rel]
                        # todo: make fin safe (no float)
                        trade_price = (base_btc_price/rel_btc_price)*(1+margin/100)
                        print("trade price: "+base+" (base) / "+rel+" (rel) "+str(trade_price))
                        # place new order
                        pass
                    else:
                        print("No price data yet...")
                        return

def bot_loop(prices_data):
    print("starting bot loop")
    strategies = [ x[:-5] for x in os.listdir(sys.path[0]+'/strategies') if x.endswith("json") ]
    bot_data = "no strats active"
    for strategy_name in strategies:
        with open(sys.path[0]+"/history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        if history['status'] == 'active':
            bot_data = "Strategy: "+strategy_name+" is active"

            with open(sys.path[0]+"/strategies/"+strategy_name+".json", 'r') as f:
                strategy = json.loads(f.read())
            bot_data = "History: "+str(history)

            # check refresh interval vs last refresh
            if history['last_refresh'] == 0 or history['last_refresh'] + strategy['refresh_interval']*60 > int(time.time()):
                history.update({'last_refresh':int(time.time())})
                print("Strategy: "+strategy_name+" refreshing orders")
                bot_data = "Strategy type: "+strategy['strategy_type']
                session = history['sessions'][str(len(history['sessions'])-1)]
                # cancel old orders
                cancel_session_orders(session)
                # place fresh orders
                submit_strategy_orders(strategy, prices_data)
                # update session history
                with open(sys.path[0]+"/history/"+strategy_name+".json", 'w+') as f:
                     f.write(json.dumps(history))
    print("bot loop completed")
    return bot_data

def orderbook_loop(node_ip, user_pass):
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
                orderbook = rpclib.orderbook(node_ip, user_pass, base, rel)
                orderbook_data.append(orderbook.json())
    print("orderbook loop completed")
    return orderbook_data
