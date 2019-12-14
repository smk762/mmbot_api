#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from . import rpclib, priceslib

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
    print("Prices data: "+str(prices_data))
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
                        rel_price = (rel_btc_price/base_btc_price)*(1+margin/100)
                        base_balance_info = rpclib.my_balance(mm2_ip, mm2_rpc_pass, base).json()
                        available_base_balance = float(base_balance_info["balance"]) - float(base_balance_info["locked_by_swaps"])
                        basevolume = available_base_balance * strategy['balance_pct']/100
                        print("trade price: "+base+" (base) / "+rel+" (rel) "+str(rel_price)+" volume = "+str(basevolume))
                        # place new order TODO: check if swap in progress.
                        if strategy['balance_pct'] != 100:
                            resp = rpclib.setprice(mm2_ip, mm2_rpc_pass, base, rel, basevolume, rel_price, False, True)
                        else:
                            resp = rpclib.setprice(mm2_ip, mm2_rpc_pass, base, str(rel), basevolume, str(rel_price), True, True)
                        print("rpclib.setprice("+mm2_ip+", "+mm2_rpc_pass+", "+base+", "+str(rel)+", "+str(rel_price))
                        print(resp.json())
                        pass
                    else:
                        print("No price data yet...")
                        return

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
            print("History: "+str(history))
            print(history['last_refresh'])
            print(str(strategy['refresh_interval']))
            print(str(time.time()))
            # check refresh interval vs last refresh
            if history['last_refresh'] == 0 or history['last_refresh'] + strategy['refresh_interval'] < int(time.time()):
                print("Refreshing strategy: "+strategy_name)
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
                orderbook = rpclib.orderbook(mm2_ip, mm2_rpc_pass, base, rel)
                orderbook_data.append(orderbook.json())
    print("orderbook loop completed")
    return orderbook_data


## Use orderbook and prices data to identigy aritrage opportunities



def run_arb_strategy(mm2_ip, mm2_rpc_pass, strategy):
    orderbook_data = orderbook_loop(mm2_ip, mm2_rpc_pass)
    prices_data = priceslib.prices_loop()
    for base in base_list:
        for rel in rel_list:
            if base != rel:
                # get binance price
                print("Binance Price: "+str())
            # check if any mm2 orders under binance price
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
