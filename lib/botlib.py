#!/usr/bin/env python3
import os
import json
import time
import requests
from . import rpclib, priceslib, binance_api, coinslib

#  LOOPS
def format_num_10f(val):
    if val != 0:
        try:
            val = "{:.10f}".format(round(float(val),10))
        except:
            pass
    return val

def orderbook_loop(mm2_ip, mm2_rpc_pass, config_path):
    active_coins = mm2_active_coins(mm2_ip, mm2_rpc_pass)
    orderbook_data = []
    for base in active_coins:
        for rel in active_coins:
            if base != rel:
                orderbook_pair = get_mm2_pair_orderbook(mm2_ip, mm2_rpc_pass, base, rel)
                orderbook_data.append(orderbook_pair)
    return orderbook_data
    
def bot_loop(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, balances_data, prices_data, config_path):
    print("starting bot loop")
    strategies = [ x[:-5] for x in os.listdir(config_path+'/strategies') if x.endswith("json") ]
    bot_data = "bot data placeholder"
    for strategy_name in strategies:
        with open(config_path+"history/"+strategy_name+".json", 'r') as f:
            history = json.loads(f.read())
        if history['Status'] == 'active':
            session_start = history['Sessions'][str(len(history['Sessions'])-1)]['Started']
            history['Sessions'][str(len(history['Sessions'])-1)].update({"Duration":int(time.time())-session_start})
            print("Active strategy: "+strategy_name)
            with open(config_path+"strategies/"+strategy_name+".json", 'r') as f:
                strategy = json.loads(f.read())
            history = update_session_swaps(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, balances_data, strategy, history)
            history = get_binance_orders_status(bn_key, bn_secret, history)
            print("session swaps updated")
            print("update total balanace deltas")
            history = calc_balance_deltas(strategy, history)
            print("total deltas updated")
            # check refresh interval vs last refresh
            refresh_time = history['Last refresh'] + strategy['Refresh interval']*60
            if history['Last refresh'] == 0 or refresh_time < int(time.time()) or history['Last refresh'] < session_start:
                active_coins = mm2_active_coins(mm2_ip, mm2_rpc_pass)
                strategy_coins = list(set(strategy['Sell list']+strategy['Buy list']))
                inactive_skip = False
                for coin in strategy_coins:
                    if coin not in active_coins:
                        inactive_skip = True
                        break
                if not inactive_skip:
                    print("*** Refreshing strategy: "+strategy_name+" ***")
                    history.update({'Last refresh':int(time.time())})
                    # cancel old orders
                    history = cancel_session_orders(mm2_ip, mm2_rpc_pass, history)
                    # place fresh orders
                    history = submit_strategy_orders(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, config_path, strategy, history)
                    # update session history
                else:
                    print("Skipping strategy "+strategy_name+": MM2 coins not active ")
            else:
                time_left = (history['Last refresh'] + strategy['Refresh interval']*60 - int(time.time()))/60
                print("Skipping strategy "+strategy_name+": waiting for refresh interval in "+str(time_left)+" min")
            with open(config_path+"history/"+strategy_name+".json", 'w+') as f:
                 f.write(json.dumps(history, indent=4))
    print("bot loop completed")
    return bot_data

def mm2_balances_loop(mm2_ip, mm2_rpc_pass, coin):
    # get mm2 balance
    balance_info = rpclib.my_balance(mm2_ip, mm2_rpc_pass, coin).json()
    if 'balance' in balance_info:
        address = balance_info['address']
        coin = balance_info['coin']
        total = balance_info['balance']
        locked = balance_info['locked_by_swaps']
        available = float(total) - float(locked)
        mm2_coin_balance_data = {
            coin: {
                    "address":address,
                    "total":format_num_10f(total),
                    "locked":format_num_10f(locked),
                    "available":format_num_10f(available),
                }                
            }
    else:
        mm2_coin_balance_data = {
            coin: {
                    "address":'loading...',
                    "total":'loading...',
                    "locked":'-',
                    "available":'-',
                }                
            }
    return mm2_coin_balance_data

def bn_balances_loop(bn_key, bn_secret, addresses_data):
    # get binance balances
    binance_balances = binance_api.get_binance_balances(bn_key, bn_secret)
    bn_balances_data = {}
    for coin in binance_balances:
        if coin in addresses_data: 
            address = addresses_data[coin]
        else:
            address = ""
        available = binance_balances[coin]['available']
        locked = binance_balances[coin]['locked']
        total = binance_balances[coin]['total']
        bn_balances_data.update({coin: {
            "address":address,
            "total":format_num_10f(total),
            "locked":format_num_10f(locked),
            "available":format_num_10f(available),
            }                
        })
    return bn_balances_data

def prices_loop():
    # TODO: include mm2 price? or do separate?
    # source > quoteasset > baseasset
    prices_data = {
        "Binance":{

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
        prices_data["Binance"][quoteAsset] = {}
        for baseAsset in binance_api.base_asset_info:
            if baseAsset in coinslib.cointags:
                if baseAsset not in prices_data["Binance"]:
                    prices_data["Binance"][baseAsset] = {}
                if baseAsset+quoteAsset in binance_prices:
                    price = float(binance_prices[baseAsset+quoteAsset])
                    if price !=- 0:
                        invert_price = 1/price
                    else: 
                        invert_price = 0
                    prices_data["Binance"][quoteAsset].update({baseAsset:invert_price})
                    prices_data["Binance"][baseAsset].update({quoteAsset:price})
    print(prices_data)
    paprika_data = requests.get("https://api.coinpaprika.com/v1/tickers?quotes=USD%2CBTC").json()
    for item in paprika_data:
        if item['symbol'] in coinslib.cointags:
            prices_data['paprika'].update({
                item['symbol']:{
                    "USD":item['quotes']['USD']['price'],
                    "BTC":item['quotes']['BTC']['price'],
                }
            })

    gecko_data = priceslib.gecko_prices(",".join(coinslib.gecko_ids), 'usd,btc').json()
    for coin in coinslib.cointags:
        usd_api_sum = 0
        btc_api_sum = 0
        btc_api_sources = []
        usd_api_sources = []
        if coinslib.coin_api_codes[coin]['coingecko_id'] != '':
            prices_data['gecko'].update({
                coin:{
                    "USD":gecko_data[coinslib.coin_api_codes[coin]['coingecko_id']]['usd'],
                    "BTC":gecko_data[coinslib.coin_api_codes[coin]['coingecko_id']]['btc'],
                }
            })
            usd_api_sum += prices_data['gecko'][coin]['USD']
            btc_api_sum += prices_data['gecko'][coin]['BTC']
            btc_api_sources.append('CoinGecko')
            usd_api_sources.append('CoinGecko')
        if coin in prices_data['paprika']:
            usd_api_sum += prices_data['paprika'][coin]['USD']
            btc_api_sum += prices_data['paprika'][coin]['BTC']
            btc_api_sources.append('CoinPaprika')
            usd_api_sources.append('CoinPaprika')
        if coin in prices_data["Binance"]:
            if 'TUSD' in prices_data["Binance"][coin]:
                usd_api_sum += prices_data["Binance"][coin]['TUSD']
                usd_api_sources.append('Binance')
            if coin == 'BTC':
                btc_api_sum += 1
                btc_api_sources.append('Binance')
            elif 'BTC' in prices_data["Binance"][coin]:
                btc_api_sum += prices_data["Binance"][coin]['BTC']
                btc_api_sources.append('Binance')
            elif coin in prices_data["Binance"]['BTC']:
                btc_api_sum += 1/prices_data["Binance"]['BTC'][coin]
                btc_api_sources.append('Binance')

        if len(usd_api_sources) > 0:
            usd_ave = usd_api_sum/len(usd_api_sources)
            btc_ave = btc_api_sum/len(btc_api_sources)
        else:
            btc_ave = 'No Data'
            usd_ave = 'No Data'
        prices_data['average'].update({
            coin:{
                "USD":usd_ave,
                "BTC":btc_ave,
                "btc_sources":btc_api_sources,
                "usd_sources":usd_api_sources
            }
        })
    print(prices_data)
    return prices_data

# MISC

def mm2_active_coins(mm2_ip, mm2_rpc_pass):
    active_coins = []
    active_coins_data = rpclib.get_enabled_coins(mm2_ip, mm2_rpc_pass).json()
    if 'result' in active_coins_data:
        for coin in active_coins_data['result']:
            active_coins.append(coin['ticker'])
    return active_coins

# STRATEGIES

def submit_strategy_orders(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, config_path, strategy, history):
    prices_data = prices_loop()
    print("*** submitting strategy orders ***")
    print("Strategy: "+str(strategy))
    if strategy['Type'] == 'margin':
        history = run_margin_strategy(mm2_ip, mm2_rpc_pass, strategy, history, prices_data)
    elif strategy['Type'] == 'arbitrage':
        history = run_arb_strategy(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, config_path, strategy, history)
    return history

def run_arb_strategy(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, config_path, strategy, history):
    orderbook_data = orderbook_loop(mm2_ip, mm2_rpc_pass, config_path)
    prices_data = prices_loop()
    # check balances
    balances = {}
    for base in strategy['Buy list']:
        for rel in strategy['Sell list']:
            if base != rel:
                for pair in orderbook_data:
                    if rel+base in pair:
                        asks = pair[rel+base]['asks']
                if len(asks) > 0:
                    best_mm2_price = 999999999999999999999999999999999
                    for item in asks:
                        mm2_price = float(item['price'])
                        if mm2_price < best_mm2_price:
                            mm2_base = item['base']
                            mm2_rel = item['rel']
                            best_mm2_price = mm2_price
                            mm2_maxvol = float(item['max_volume'])
                    print("** BEST MM2 PRICE: "+str(best_mm2_price))

                    best_bn_price = 999999999999999999999999999999999
                    # Check for direct binance price
                    if base+rel in binance_api.binance_pairs:
                        binance_price = float(binance_api.get_price(bn_key, base+rel)['price'])
                        if binance_price < best_bn_price:
                            best_bn_price = binance_price
                            source = "Direct "+base+rel
                    elif rel+base in binance_api.binance_pairs:
                        binance_price = float(binance_api.get_price(bn_key, rel+base)['price'])
                        if binance_price < best_bn_price:
                            best_bn_price = binance_price
                            source = "Direct "+rel+base
                    # Get indirect binance prices
                    common_quote_assets = binance_api.get_binance_common_quoteAsset(base, rel)
                    for quote in common_quote_assets:
                        if quote not in [base, rel]:
                            base_quote_price = binance_api.get_price(bn_key, base+quote)
                            if 'price' in base_quote_price:
                                base_quote_price = float(base_quote_price['price'])
                            rel_quote_price = binance_api.get_price(bn_key, rel+quote)
                            if 'price' in rel_quote_price:
                                rel_quote_price = float(rel_quote_price['price'])
                            binance_price = rel_quote_price/base_quote_price
                            if binance_price < best_bn_price:
                                best_bn_price = binance_price
                                source = "Indirect via "+rel+quote+" & "+base+quote
                    print("** BEST BINANCE PRICE: "+str(best_bn_price)+" ("+source+")")
                    pct = (best_mm2_price/best_bn_price-1)*100
                    if pct < -1*strategy['Margin']:
                        print("*** ARB OPPORTUNITY! *** (pct vs binance best = "+str(pct)+"%)")
                        # buy base, sell rel. 
                        mm2_rel_bal = float(rpclib.my_balance(mm2_ip, mm2_rpc_pass, mm2_rel).json()['balance'])*strategy["Balance pct"]/100
                        mm2_trade_fee = float(rpclib.get_fee(mm2_ip, mm2_rpc_pass, mm2_rel).json()['result']['amount'])*2
                        mm2_vol = (mm2_rel_bal-mm2_trade_fee)/best_mm2_price
                        if base in prices_data['average']:
                            trade_val = mm2_vol*prices_data['average'][mm2_base]['USD']
                        if trade_val > 5:
                            resp = rpclib.buy(mm2_ip, mm2_rpc_pass, mm2_base, mm2_rel, mm2_vol, best_mm2_price).json()
                            print(resp)
                            if 'result' in resp:
                                session = str(len(history['Sessions'])-1)
                                history['Sessions'][session]['MM2 open orders'].append(resp['result']['uuid'])
                        else:
                            print("Skipping, below USD$5 trade value") 
                    print("---------------------------------------------------------")
    return history

def run_margin_strategy(mm2_ip, mm2_rpc_pass, strategy, history, prices_data):
    uuids = []
    for rel in strategy['Buy list']:
        for base in strategy['Sell list']:
            if base != rel:
                # in case prices data not yet populated
                if base in prices_data['average']:
                    base_btc_price = prices_data['average'][base]['BTC']
                    rel_btc_price = prices_data['average'][rel]['BTC']
                    # todo: make fin safe (no float)
                    rel_price = (base_btc_price/rel_btc_price)*(1+strategy['Margin']/100)
                    base_balance_info = rpclib.my_balance(mm2_ip, mm2_rpc_pass, base).json()
                    available_base_balance = float(base_balance_info["balance"]) - float(base_balance_info["locked_by_swaps"])
                    basevolume = available_base_balance * strategy['Balance pct']/100
                    print("trade price: "+base+" (base) / "+rel+" (rel) "+str(rel_price)+" volume = "+str(basevolume))
                    if strategy['Balance pct'] != 100:
                        resp = rpclib.setprice(mm2_ip, mm2_rpc_pass, base, rel, basevolume, rel_price, False, True)
                    else:
                        resp = rpclib.setprice(mm2_ip, mm2_rpc_pass, base, rel, basevolume, rel_price, True, True)
                    print("Setprice Order created: " + str(resp.json()))
                    uuid = resp.json()['result']['uuid']
                    uuids.append(uuid)
                else:
                    print("No price data yet...")
    history['Sessions'][str(len(history['Sessions'])-1)]['MM2 open orders'] = uuids
    return history
    # update session history with open orders

def get_mm2_swap_status(mm2_ip, mm2_rpc_pass, swap):
    print("checking mm2 swap "+swap)
    swap_data = rpclib.my_swap_status(mm2_ip, mm2_rpc_pass, swap).json()
    if 'result' in swap_data:
        for event in swap_data['result']['events']:
            if event['event']['type'] in rpclib.error_events: 
                status = 'Failed'
                break
            if event['event']['type'] == 'Finished':
                status = 'Finished'
            else:
                status = event['event']['type']
    else: 
        print(swap_data)
    return status, swap_data['result']

def update_session_swaps(mm2_ip, mm2_rpc_pass, bn_key, bn_secret, balances_data, strategy, history):
    for session in history['Sessions']:
        mm2_order_uuids = history['Sessions'][session]['MM2 open orders']
        for order_uuid in mm2_order_uuids:
            print("order: "+order_uuid)
            order_info = rpclib.order_status(mm2_ip, mm2_rpc_pass, order_uuid).json()
            if 'order' in order_info:
                swaps = order_info['order']['started_swaps']
                print("swaps: "+str(swaps))
                for swap in swaps:
                    if swap not in history['Sessions'][session]['MM2 swaps in progress']:
                        history['Sessions'][session]['MM2 swaps in progress'].append(swap)
            elif 'error' in order_info:
                print("order_info error: "+str(order_info))
                swap_status = rpclib.my_swap_status(mm2_ip, mm2_rpc_pass, order_uuid).json()
                print(swap_status)
                if 'result' in swap_status:
                    if order_uuid not in history['Sessions'][session]['MM2 swaps in progress']:
                        history['Sessions'][session]['MM2 swaps in progress'].append(order_uuid)
                else:
                    mm2_order_uuids.remove(order_uuid)
            else:
                print("order_info: "+str(order_info))
        swaps_in_progress = history['Sessions'][session]['MM2 swaps in progress']
        for swap in swaps_in_progress:
            swap_status = get_mm2_swap_status(mm2_ip, mm2_rpc_pass, swap)
            status = swap_status[0]
            swap_data = swap_status[1]
            print(swap+" status: "+status)
            if status == 'Finished':
                print("adding to session deltas")
                if "my_info" in swap_data:
                    print("updating session deltas history")
                    history['Sessions'][session]['MM2 swaps completed'].update({
                                                        swap:{
                                                            "Recieved coin":swap_data["my_info"]["other_coin"],
                                                            "Recieved amount":float(swap_data["my_info"]["other_amount"]),
                                                            "Sent coin":swap_data["my_info"]["my_coin"],
                                                            "Sent amount":float(swap_data["my_info"]["my_amount"]),
                                                            "Start time":swap_data["my_info"]["started_at"]
                                                        }
                                                    })
                    swaps_in_progress.remove(swap)
                    print("init cex counterswap ["+swap+"]")
                    history = start_cex_counterswap(bn_key, bn_secret, strategy, history, balances_data, session, swap)
                    print("submitted cex counterswap  ["+swap+"]")
                else:
                    print(swap+" data: "+str(swap_data))
            elif status == 'Failed':
                swaps_in_progress.remove(swap)
        history['Sessions'][session]['MM2 swaps in progress'] = swaps_in_progress
        history['Sessions'][session]['MM2 open orders'] = mm2_order_uuids
    return history

def get_binance_orders_status(bn_key, bn_secret, history):
    for session in history['Sessions']:
        if "Binance" in history['Sessions'][session]["CEX open orders"]:
            for mm2_uuid in history['Sessions'][session]["CEX open orders"]["Binance"]:
                add_symbols = []
                rem_symbols = []
                for symbol in history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid]:
                    print(symbol)
                    print(history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid])
                    if 'orderId' in history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid][symbol]:
                        orderId = history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid][symbol]['orderId']
                        resp = binance_api.get_order(bn_key, bn_secret, symbol, orderId)
                        if "status" in resp:
                            if resp['status'] == 'FILLED':
                                # move to "completed"
                                if mm2_uuid not in history['Sessions'][session]["CEX swaps completed"]["Binance"]:
                                    history['Sessions'][session]["CEX swaps completed"]["Binance"].update({mm2_uuid:{}})
                                history['Sessions'][session]["CEX swaps completed"]["Binance"][mm2_uuid].update({symbol:resp})
                                # remove from open
                                rem_symbols.append(symbol)
                            else:
                                add_symbols.append({symbol:resp})
                        else:
                            print(resp)
                    elif 'error' in history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid][symbol]:
                        resp = history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid][symbol]
                        if resp["type"] == "SELL":
                            reorder = binance_api.create_sell_order(bn_key, bn_secret, symbol, resp["Amount"], resp["Price"])
                            if 'orderId' in reorder:
                                history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid].update({symbol: reorder})
                        elif resp["type"] == "BUY":
                            reorder = binance_api.create_buy_order(bn_key, bn_secret, symbol, resp["Amount"], resp["Price"])
                            if 'orderId' in reorder:
                                history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid].update({symbol: reorder})
                for symbol_resp in add_symbols:
                    history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid].update(symbol_resp)
                for symbol in rem_symbols:
                    if symbol in history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid]:
                        history['Sessions'][session]["CEX open orders"]["Binance"][mm2_uuid].pop(symbol)
    return history

def start_cex_counterswap(bn_key, bn_secret, strategy, history, balances_data, session_num, mm2_swap_uuid):
    mm2_swap_data = history['Sessions'][session_num]['MM2 swaps completed'][mm2_swap_uuid]
    replenish_coin = mm2_swap_data["Sent coin"]
    replenish_amount = float(mm2_swap_data["Sent amount"])
    spend_coin = mm2_swap_data["Recieved coin"]
    spend_amount = float(mm2_swap_data["Recieved amount"])
    if "Binance" in strategy["CEX countertrade list"]:
        symbols = binance_api.get_binance_countertrade_symbols(bn_key, bn_secret, balances_data["Binance"], replenish_coin, spend_coin, replenish_amount, spend_amount)
        if symbols[0] is not False:
            if symbols[0] == symbols[1]:
                history = start_direct_trade(bn_key, bn_secret, strategy, history, session_num, mm2_swap_uuid,
                                   replenish_coin, spend_coin, replenish_amount, spend_amount, symbols[0])
            else:
                history = start_indirect_trade(bn_key, bn_secret, strategy, history, session_num, mm2_swap_uuid,
                                     replenish_coin, spend_coin, replenish_amount, spend_amount, symbols[0], symbols[1])
        else:
            print("countertrade symbols not found")
    return history

def start_direct_trade(bn_key, bn_secret, strategy, history, session_num, mm2_swap_uuid,
                       replenish_coin, spend_coin, replenish_amount, spend_amount, symbol):
    margin = strategy["Margin"]
    replenish_amount = binance_api.round_to_tick(symbol, replenish_amount)
    spend_amount = binance_api.round_to_tick(symbol, spend_amount)
    if mm2_swap_uuid not in history['Sessions'][session_num]["CEX open orders"]["Binance"]:
        history['Sessions'][session_num]["CEX open orders"]["Binance"].update({mm2_swap_uuid:{}})
    if binance_api.binance_pair_info[symbol]['quoteAsset'] == replenish_coin:
        # E.g. Replenish BTC, Spend KMD
        # Spend Amount = 10000 (KMD)
        # replenish_amount = 0.777 (BTC)
        # symbol = KMDBTC
        # quoteAsset = BTC
        # Margin = 2%
        price = float(replenish_amount)/float(spend_amount)*(100+margin)/100
        price = binance_api.round_to_tick(symbol, price)
        # Sell 10000 KMD for 0.79254 BTC
        resp = binance_api.create_sell_order(bn_key, bn_secret, symbol, spend_amount, price)
        if 'orderId' in resp:
            history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({symbol: resp})
        else:
            history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({symbol: {
                        "error": "Sell "+symbol+" failed - "+resp['msg'],
                        "type":"SELL",
                        "Amount":spend_amount,
                        "Price":format_num_10f(price)
                    }
                })
    else:
        # E.g. Replenish KMD, Spend BTC
        # replenish_amount = 10000 (KMD)
        # Spend Amount = 0.777 (BTC)
        # symbol = KMDBTC
        # quoteAsset = BTC
        # Margin = 2%
        price = float(replenish_amount)/float(spend_amount)*(100-margin)/100
        price = binance_api.round_to_tick(symbol, price)
        # Replenish 10000 KMD, spending 0.7614 BTC
        resp = binance_api.create_buy_order(bn_key, bn_secret, symbol, replenish_amount, price)
        if 'orderId' in resp:
            history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({symbol: resp})
        else:
            history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({symbol: {
                        "error": "Sell "+symbol+" failed - "+resp['msg'],
                        "type":"BUY",
                        "Amount":replenish_amount,
                        "Price":format_num_10f(price)
                    }
                })
    return history

def start_indirect_trade(bn_key, bn_secret, strategy, history, session_num, mm2_swap_uuid,
                         replenish_coin, spend_coin, replenish_amount, spend_amount, spend_symbol, replenish_symbol):

    margin = strategy["Margin"]
    mm2_trade_price = replenish_amount/spend_amount
    inverse_mm2_trade_price = spend_amount/replenish_amount

    margin_trade_buy_price = mm2_trade_price*(100-margin)/100
    margin_trade_sell_price = mm2_trade_price*(100+margin)/100

    # E.g. Spend KMD, Replenish DASH
    # replenish_amount = 1 (DASH)
    # Spend Amount = 100 (KMD)
    # replenish_symbol = DASHBTC
    # spend_symbol = KMDBTC
    # quoteAsset = BTC
    # Margin = 2%

    # i.e KMDBTC price
    spend_quote_price = float(binance_api.get_price(bn_key, spend_symbol)['price'])
    spend_quote_amount = binance_api.round_to_tick(spend_symbol, spend_amount*spend_quote_price)

    # i.e DASHBTC price
    replenish_quote_price = float(binance_api.get_price(bn_key, replenish_symbol)['price'])
    rep_quote_amount = binance_api.round_to_tick(spend_symbol, spend_amount*spend_quote_price)

    # i.e. DASHKMD price (should be close to mm2_trade price after margin applied)
    rep_spend_price = replenish_quote_price/spend_quote_price

    # i.e. KMDDASH price (should be close to inverse mm2_trade price after margin applied)
    spend_rep_price = spend_quote_price/replenish_quote_price

    if mm2_swap_uuid not in history['Sessions'][session_num]["CEX open orders"]["Binance"]:
        history['Sessions'][session_num]["CEX open orders"]["Binance"].update({mm2_swap_uuid:{}})
    while float(rep_quote_amount) > float(spend_quote_amount)*(100+margin)/100:
        replenish_quote_price = replenish_quote_price*0.999
        replenish_amount = binance_api.round_to_tick(replenish_symbol, replenish_amount)
        rep_quote_amount = spend_amount*spend_quote_price
    # Replenish spent BTC, spending DASH
    resp = binance_api.create_sell_order(bn_key, bn_secret, spend_symbol, float(spend_amount), spend_quote_price)
    if 'orderId' in resp:
        history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({spend_symbol: resp})
    else:
        history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({spend_symbol: {
                    "error": "Sell "+spend_symbol+" failed - "+resp['msg'],
                    "type":"SELL",
                    "Amount":spend_amount,
                    "Price":format_num_10f(spend_quote_price)
                }
            })

    # Replenish 100 KMD, spending BTC 
    resp = binance_api.create_buy_order(bn_key, bn_secret, replenish_symbol, float(replenish_amount), replenish_quote_price)
    if 'orderId' in resp:
        history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({replenish_symbol: resp})
    else:
        history['Sessions'][session_num]["CEX open orders"]["Binance"][mm2_swap_uuid].update({replenish_symbol: {
                    "error": "Sell "+replenish_symbol+" failed - "+resp['msg'],
                    "type":"SELL",
                    "Amount":replenish_amount,
                    "Price":format_num_10f(replenish_quote_price)
                }
            })
    return history

def calc_balance_deltas(strategy, history):
    strategy_coins = list(set(strategy['Sell list']+strategy['Buy list']))

    total_balance_deltas = {}
    total_cex_completed_swaps = 0
    total_cex_unfinished_swaps = 0
    total_mm2_completed_swaps = 0

    for strategy_coin in strategy_coins:
        total_balance_deltas.update({strategy_coin:0})

    for session in history['Sessions']:
        session_balance_deltas = {}
        session_mm2_completed_swaps = 0
        session_cex_completed_swaps = 0
        session_cex_unfinished_swaps = 0
        mm2_swaps = history['Sessions'][session]['MM2 swaps completed']
        binance_swaps = history['Sessions'][session]["CEX swaps completed"]["Binance"]
        unfinished_binance_swaps = history['Sessions'][session]["CEX open orders"]["Binance"]

        for strategy_coin in strategy_coins:
            session_balance_deltas.update({strategy_coin:0})

        for uuid in mm2_swaps:
            session_mm2_completed_swaps += 1
            total_mm2_completed_swaps += 1

            swap_info = mm2_swaps[uuid]
            swap_rec_coin = swap_info["Recieved coin"]
            swap_rec_amount = swap_info["Recieved amount"]
            swap_spent_coin = swap_info["Sent coin"]
            swap_spent_amount = swap_info["Sent amount"]

            session_balance_deltas[swap_rec_coin] += round(swap_rec_amount,10)
            session_balance_deltas[swap_spent_coin] -= round(swap_spent_amount,10)
            total_balance_deltas[swap_rec_coin] += round(swap_rec_amount,10)
            total_balance_deltas[swap_spent_coin] -= round(swap_spent_amount,10)

        for uuid in unfinished_binance_swaps:
            for symbol in unfinished_binance_swaps[uuid]:
                session_cex_unfinished_swaps += 1
                total_cex_unfinished_swaps += 1

        for uuid in binance_swaps:
            for symbol in binance_swaps[uuid]:
                session_cex_completed_swaps += 1
                total_cex_completed_swaps += 1

                quoteAsset = binance_api.binance_pair_info[symbol]['quoteAsset']
                baseAsset = binance_api.binance_pair_info[symbol]['baseAsset'] 

                if quoteAsset not in session_balance_deltas:
                    session_balance_deltas.update({strategy_coin:0})
                if quoteAsset not in total_balance_deltas:
                    total_balance_deltas.update({strategy_coin:0})

                swap_info = binance_swaps[uuid][symbol]
                if swap_info['side'] == 'BUY':
                    swap_rec_coin = baseAsset
                    swap_spent_coin = quoteAsset
                    swap_rec_amount = swap_info["executedQty"]
                    swap_spent_amount = swap_info["cummulativeQuoteQty"]
                elif swap_info['side'] == 'SELL':
                    swap_spent_coin = baseAsset
                    swap_rec_coin = quoteAsset
                    swap_spent_amount = swap_info["executedQty"]
                    swap_rec_amount = swap_info["cummulativeQuoteQty"]

                session_balance_deltas[swap_rec_coin] += round(float(swap_rec_amount),10)
                session_balance_deltas[swap_spent_coin] -= round(float(swap_spent_amount),10)
                total_balance_deltas[swap_rec_coin] += round(float(swap_rec_amount),10)
                total_balance_deltas[swap_spent_coin] -= round(float(swap_spent_amount),10)

        history["Sessions"][session].update({
                "Balance Deltas": session_balance_deltas,
                "Session MM2 swaps completed":session_mm2_completed_swaps,
                "Session CEX swaps completed":session_cex_completed_swaps,
                "Session CEX swaps unfinished":session_cex_unfinished_swaps
            })

    history.update({
            "Total MM2 swaps completed": total_mm2_completed_swaps,
            "Total CEX swaps unfinished": total_cex_unfinished_swaps,
            "Total CEX swaps completed": total_cex_completed_swaps,
            "Total balance deltas": total_balance_deltas,
        })
    return history

def cancel_strategy(mm2_ip, mm2_rpc_pass, history, strategy):
    if len(history['Sessions']) > 0:
        session = history['Sessions'][str(len(history['Sessions'])-1)]
        # calc session duration
        started_at = session['Started']
        last_refresh = history["Last refresh"]
        if last_refresh - int(time.time()) > strategy["Refresh interval"]*60:
            duration = last_refresh - started_at
        else:
            duration = int(time.time()) - started_at
        session.update({"Duration":duration})
        # cancel mm2 orders
        mm2_open_orders = session["MM2 open orders"]
        for order_uuid in mm2_open_orders:
            rpclib.cancel_uuid(mm2_ip, mm2_rpc_pass, order_uuid)
        session.update({"MM2 open orders":[]})
        history['Sessions'].update({str(len(history['Sessions'])-1):session})
    return history

def cancel_session_orders(mm2_ip, mm2_rpc_pass, history):
    print("cancelling session orders")
    session = str(len(history['Sessions'])-1)
    # Cancel MM2 Orders
    mm2_order_uuids = history['Sessions'][str(len(history['Sessions'])-1)]['MM2 open orders']
    print(mm2_order_uuids)
    for order_uuid in mm2_order_uuids:
        print(order_uuid)
        order_info = rpclib.order_status(mm2_ip, mm2_rpc_pass, order_uuid).json()
        swap_in_progress = False
        if 'order' in order_info:
            swaps = order_info['order']['started_swaps']
            print(swaps)
            # updates swaps
            for swap in swaps:
                swap_status = get_mm2_swap_status(mm2_ip, mm2_rpc_pass, swap)
                status = swap_status[0]
                swap_data = swap_status[1]
                print(swap+": "+status)
                if status != 'Finished' and status != 'Failed':
                    # swap in progress
                    swap_in_progress = True
                    if swap not in history['Sessions'][session]['MM2 swaps in progress']:
                        history['Sessions'][session]['MM2 swaps in progress'].append(swap)
        else:
            print(order_info)
        if not swap_in_progress:
            rpclib.cancel_uuid(mm2_ip, mm2_rpc_pass, order_uuid)

    history['Sessions'][str(len(history['Sessions'])-1)]['MM2 open orders'] = []
    return history

# JSON FILES INITIALIZATION

def init_strategy(name, strategy_type, sell_list, buy_list, margin, refresh_interval, balance_pct, cex_list, config_path):
    strategy = {
        "Name":name,
        "Type":strategy_type,
        "Sell list":sell_list,
        "Buy list":buy_list,
        "Margin":margin,
        "Refresh interval":refresh_interval,
        "Balance pct":balance_pct,
        "CEX countertrade list":cex_list
    }
    with open(config_path+"strategies/"+name+'.json', 'w+') as f:
        f.write(json.dumps(strategy, indent=4))
    balance_deltas = {}
    strategy_coins = list(set(sell_list+buy_list))
    for strategy_coin in strategy_coins:
        balance_deltas.update({strategy_coin:0})
    history = { 
        "Sessions":{},
        "Last refresh": 0,
        "Total MM2 swaps completed": 0,
        "Total CEX swaps completed": 0,
        "Total CEX swaps unfinished": 0,
        "Total balance deltas": balance_deltas,
        "Status":"inactive"
    }
    with open(config_path+"history/"+name+".json", 'w+') as f:
        f.write(json.dumps(history, indent=4))
    return strategy

def init_session(strategy_name, strategy, history, config_path):
    history.update({"Status":"active"})
    # init balance datas
    balance_deltas = {}
    for rel in strategy["Sell list"]:
        balance_deltas.update({rel:0})
    for base in strategy["Buy list"]:
        if base not in strategy["Sell list"]:
            balance_deltas.update({base:0})
    # init session
    sessions = history['Sessions']
    sessions.update({str(len(sessions)):{
            "Started":int(time.time()),
            "Duration":0,
            "MM2 open orders": [],
            "MM2 swaps in progress": [],
            "MM2 swaps completed": {},
            "CEX open orders": {
                    "Binance": {}
                },
            "CEX swaps completed": {
                    "Binance": {}
                },
            "Balance Deltas": balance_deltas,
            "Session MM2 swaps completed": 0,
            "Session CEX swaps unfinished": 0,
            "Session CEX swaps completed": 0
        }})
    history.update({"Sessions":sessions})
    with open(config_path+"history/"+strategy_name+".json", 'w+') as f:
        f.write(json.dumps(history, indent=4))
    with open(config_path+"strategies/"+strategy_name+".json", 'w+') as f:
        f.write(json.dumps(strategy, indent=4))

# REVIEW 

def get_mm2_pair_orderbook(mm2_ip, mm2_rpc_pass, base, rel):
    orderbook = rpclib.orderbook(mm2_ip, mm2_rpc_pass, base, rel).json()
    asks = []
    bids = []
    orderbook_pair = {
        base+rel: {
            "asks":asks,
            "bids":bids
        }
    }
    if 'asks' in orderbook:
        for order in orderbook['asks']:
            ask = {
                "base": base,
                "rel": rel,
                "price": order['price'],
                "max_volume":order['maxvolume'],
                "age":order['age']
            }
            asks.append(ask)
    if 'bids' in orderbook:
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

def get_user_addresses(mm2_ip, mm2_rpc_pass, bn_key, bn_secret):
    bn_addr = binance_api.get_binance_addresses(bn_key, bn_secret)
    mm2_addr = rpclib.all_addresses(mm2_ip, mm2_rpc_pass)
    addresses = {
        "Binance": bn_addr ,
        'mm2': mm2_addr
    }
    return addresses