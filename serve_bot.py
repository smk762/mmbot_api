#!/usr/bin/env python3
from fastapi import FastAPI
from pydantic import BaseModel
import rpclib

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Welcome to Antara Markerbot API. See /docs for all methods"}

@app.post("/balance/{coin}")
async def get_balance(userip: str, userpass: str, coin: str):
    balance_info = rpclib.my_balance(userip, userpass, coin).json()
    return balance_info

# credentials in post are insecure. getting from external file may be required.


'''
start_strategy strategy_params -> result, strategy_id
method: auth auth_key: testing_key -> result: success message: succesful auth
method: start_trade strategy: marketmaking``margin: 10 tickers_base: [BTC, KMD] tickers_rel: [VRSC]
method: get_trading_status -> result: success list_of_strategies_working: [1,2,3]


stop_strategy strategy_id -> result
started_strategies_list -> list_with_ids 
history_strategies_list -> displaying `active` and `history` (stopped) of strategies
strategy_info strategy_id -> info with params and some events maybe (at least amount of events)
strategy_events strategy_id <depth> -> displaying events (trades/transfers and etc) for strategy with optional depth (amount of last events to show) argument
'''

# strategies examples - https://github.com/CoinAlpha/hummingbot/tree/master/documentation/docs/strategies

# User sends auth, opens websocket connection, send response. If auth fails, close connection.
# if authenticated, keep connection alive, and listen for commands. Periodically, or when required, send updates.

## API methods

# authenticate_mm2(userpass, ip). same as req for mm2.
# authenticate_cex(cex_name, cex_api, cex_secret).

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

# define_strategy_template(rel_list, base_list, margin, refresh_interval=30 (optional, minutes), balance_pct=100 (optional, default 100), cex_countertrade=None (optional, cex_name or None)
# create trade strategy template, saved locally on client for future use. same params as "start_trading", but does not initiate bot loop.

# get_active_strategies()
# show list of strategies currently in progress.

# arbitrage(cex_list, coin_pair, min_profit_pct)
# for a given coin_pair (e.g. KMDBTC), monitor all cex on the list, and mm2 for prices. If price differential between exchanges exceeds min_profit_pct, execute matching trades to take advantage.




