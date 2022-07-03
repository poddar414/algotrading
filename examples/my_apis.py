import logging
from kiteconnect import KiteConnect
import time
import json
import datetime
import numpy as np

not_sale_list=['LIQUIDBEES','NIFTYBEES','MON100', 'TATAMOTORS', 'JUNIORBEES', 'BSE', 'DMART', 'INDHOTEL',  'M&M']

def my_init(debug_time,data_path='E:\\kite\\pykiteconnect\\history\\',samples_per_decision=40,consider_holdings=True,debug_session=False):

    trading_session = False
    
    # Check if login is required or not
    system_time = time.localtime(time.time())
    if debug_session==False:
    #if True:
        kite = kite_login()
        offset = -samples_per_decision # load minimum number of samples from file # offset is assumed to be only negative
        debug_session = False
        holdings = kite.holdings()
    else:
        kite = 'NULL'

        with open('E:\\kite\\history\\daily\\holdings.json', 'r') as f:
            holdings = json.load(f)        
    
        with open(data_path+'NSE_NIFTYBEES_.txt', 'r') as file:
            json_data = file.read()
            lines = json_data.split("\n")
        file.close()
        
        yr_ref,mnth_ref,date_ref = debug_time.split()[0].split('-')
        hr_ref,min_ref,sec_ref = debug_time.split()[1].split(':')

        for offset, line in enumerate(lines[0:-1]):
            json_acceptable_string = line.replace("'", "\"")
            line = json.loads(json_acceptable_string)
            timestamp = line['timestamp']
            yr,mnth,date = timestamp.split()[0].split('-')
            hr,min,sec = timestamp.split()[1].split(':')
            if(((int(yr_ref) == int(yr)) and (int(mnth_ref) == int(mnth)) and (int(date_ref) == int(date))) and (int(hr) >= int(hr_ref)) and (int(min) >= int(min_ref)) and (int(sec) >= int(sec_ref))):
                break
            
        offset = offset - len(lines) # offset is assumed to be only negative

    watch_list = prep_watch_list('E:\\kite\\history\\watch_list.txt')

    watch_list.append({'tradingsymbol':'NSE:NIFTYBEES','weight':1.0,'last_price':0.0})
    watch_list.append({'tradingsymbol':'NSE:JUNIORBEES','weight':1.0,'last_price':0.0})
    watch_list.append({'tradingsymbol':'NSE:MON100','weight':1.0,'last_price':0.0})

    if consider_holdings == True:
        for holding in holdings: # IN DEBUG SESSION read txt files and determine holdings. 
            stock_name = holding['tradingsymbol']
            stock_name = stock_name.replace("*","")
            if stock_name != 'LIQUIDBEES':
                already_present = False
                for watch in watch_list:
                    if watch['tradingsymbol'].split(':')[1] == stock_name:
                        already_present = True
                if already_present == False:
                    watch_list.append({'tradingsymbol':'NSE:'+stock_name,'weight':1.0,'last_price':1.0})


    watch_list_trading_symbol=[item['tradingsymbol'] for item in watch_list]
    buy_trigger = np.zeros(len(watch_list_trading_symbol))
    sell_trigger = np.zeros(len(watch_list_trading_symbol))

    return kite, buy_trigger, sell_trigger, watch_list_trading_symbol, trading_session, debug_session,offset, holdings

def kite_login():
    my_api_key = '25v2r7e956zj2jk1'
    my_api_secret= 'yxleie0cike2sai7dwm4459v72tqlylk'
    kite = KiteConnect(api_key=my_api_key,debug=False)
    print("Authenticate for sale")
    print(kite.login_url())
    print("Enter request token")
    request_token = input()
    data = kite.generate_session(request_token, my_api_secret)
    kite.set_access_token(data["access_token"])
    return kite

def read_watch_list_from_file(file_name):
    with open(file_name) as f:
        lines = f.readlines()
    f.close()
    return lines

def prep_watch_list(watch_list_file):
    current_watch_list=[]

    lines = read_watch_list_from_file(watch_list_file)
    for line in lines:
        line_split = line.split()
        stock_name = line_split[0]

        last_price = 1.0
        weight = 1.0

        entry = {'tradingsymbol':'NSE:'+stock_name,'weight':weight,'last_price':last_price}
        
        already_in_list = False
        for item in current_watch_list:
            if item['tradingsymbol'] == 'NSE:'+stock_name:
                already_in_list = True

        if already_in_list == False: 
            current_watch_list.append(entry)

    res_list = []
    for i in range(len(current_watch_list)):
        if current_watch_list[i] not in current_watch_list[i + 1:]:
            res_list.append(current_watch_list[i])

    return res_list

def dump_last_prices(last_prices, watch_list, samples_per_decision, data_path='E:\\kite\\pykiteconnect\\history\\'):
    for stock in watch_list:
        with open(data_path+stock.replace(':',"_")+'_.txt', 'a') as file:
            for line in last_prices[stock][samples_per_decision:]:
                file.write(json.dumps(json.loads(line)))
                file.write('\n')
        file.close()

def update_last_price(last_prices,kite, stock, my_logger=None):
    
    try:
        quote = kite.quote(stock)
    except Exception as e:
        got_ltp = False
        my_logger.debug("First try of the {} quote failed \n".format(stock))
        while got_ltp == False:
            time.sleep(5)
            try:
                quote = kite.quote(stock)
                got_ltp = True
            except Exception as e2:
                my_logger.debug(" Not getting the {} last price \n".format(stock))


    quote[stock]['timestamp'] = str(quote[stock]['timestamp'])

    my_logger.debug("{} stock Ltp is {} ".format(stock,quote[stock]["last_price"]))
    my_logger.debug("{} stock timestamp is {} ".format(stock,quote[stock]["timestamp"]))

    if(stock != 'NSE:NIFTY 50'):
        quote[stock]['last_trade_time'] = str(quote[stock]['last_trade_time'])
    last_prices[stock].append(json.dumps(quote[stock]))     # convert dictionary to string and then append       


def sample_last_prices(last_prices,stock,samples_per_decision=20,offset=-1,my_logger=None):
    
    is_possible= False

    cum_time_list = []
    time_list = []

    cur_volume_list = []
    volume_list =[]

    price_list =[]
    timestamp = '0-0-0 0:0:0'
    lines = last_prices

    buy_quantity = []
    sell_quantity = []
    over_deamnd = 1
    over_deamnd_tiny = 1

    if len(lines) < 4000000:
        local_debug = False
    else:
        local_debug = False

    # offset is assumed to be only negative
    if (samples_per_decision <= len(lines)) and (abs(offset) <= len(lines) and ((offset+samples_per_decision) <= 0)):
        
        if offset+samples_per_decision == 0:
            selected_lines = lines[offset:]    
        else:    
            selected_lines = lines[offset:offset+samples_per_decision]

        is_possible = True
    else:
        is_possible = False

    if is_possible == True:  

        consider_only_end_points = False

        isEnmptyLinePresent = False
        for line in selected_lines:
            if line == '':
                isEnmptyLinePresent = True

        if isEnmptyLinePresent == True:        
            selected_lines.remove('')

        if consider_only_end_points == True:
            selected_lines = [selected_lines[0], selected_lines[-1]] # correct problem because of new line

        json_acceptable_string = selected_lines[0].replace("'", "\"")
        line = json.loads(json_acceptable_string)

        timestamp = line['timestamp']
        last_price = line['last_price']
        price_list.append(line['last_price'])
        volume_list.append(line['volume'])
        time_list.append(0)
        prev_time_obj = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        day_cross_over = 0
        last_day_max_volume = 0

        if local_debug == True:
            my_logger.debug("{} stock total line lengths are {} ".format(stock,len(selected_lines)))
            my_logger.debug("{} stock first line is  {} ".format(stock,selected_lines[0]))
            my_logger.debug("{} stock last line is  {} ".format(stock,selected_lines[-1]))

        for idx, line in enumerate(selected_lines[1:]):
            if (line != '\n') and line != '':
                json_acceptable_string = line.replace("'", "\"")
                line = json.loads(json_acceptable_string)

                timestamp = line['timestamp']
                last_price = line['last_price']
                volume = line['volume']

                if local_debug == True:
                    my_logger.debug("{} --> {} stock last_price is {} timestamp is {} ".format(idx, stock, last_price, timestamp))

                if 'buy_quantity' in line:
                    buy_quantity.append(line['buy_quantity'])
                else:
                    buy_quantity.append(1)

                if 'sell_quantity' in line:
                    sell_quantity.append(line['sell_quantity'])
                else:
                    sell_quantity.append(1)

                price_list.append(last_price)
                cur_time_obj = prev_time_obj
                cur_time_obj = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                time_elapsed = (cur_time_obj.tm_hour - prev_time_obj.tm_hour)*60*60 + (cur_time_obj.tm_min - prev_time_obj.tm_min)*60+(cur_time_obj.tm_sec - prev_time_obj.tm_sec)
                
                if time_elapsed < 60*15 and time_elapsed > 0: # if time elapsed is less than 15min
                    time_list.append(time_elapsed)

                    if (day_cross_over == 0):
                        volume_list.append(volume)
                    else:
                        volume_list.append(last_day_max_volume + volume)
                    if local_debug == True:
                        my_logger.debug("{} stock time elapsed is {} ".format(stock,time_elapsed))

                elif cur_time_obj.tm_mday != prev_time_obj.tm_mday: # day cross over
                    time_list.append(0.0001)
                    day_cross_over = 1
                    last_day_max_volume = volume_list[-1]
                    volume_list.append(last_day_max_volume + volume) #max(volume_list) is the last maximum volume pf previous day
                    if local_debug == True:
                        my_logger.debug("{} stock time elapsed is {} ".format(stock,0.1))
                    #print('day cross over happened with previous day volume {} and fresh volume {}'.format(last_day_max_volume,volume))
                elif time_elapsed == 0:
                    time_list.append(0.0001)
                    if (day_cross_over == 0):
                        volume_list.append(volume)
                    else:
                        volume_list.append(last_day_max_volume + volume)

                    if local_debug == True:
                        my_logger.debug("{} stock time elapsed is {} ".format(stock,0.2))
                #    my_logger.debug('skipping the time stamp')
                else: # otherwise dont consider this time tics
                    price_list = price_list[:-1]
                    print("something gone wrong in time calculation cur_time {} prev_time {}".format(cur_time_obj,prev_time_obj))
                    my_logger.debug("something gone wrong in time calculation cur_time {} prev_time {}".format(cur_time_obj,prev_time_obj))

                prev_time_obj = cur_time_obj

        cum_time_list = [sum(time_list[0:x:1]) for x in range(1, len(time_list)+1)]   

        prev_x = cum_time_list[0]
        for curx in cum_time_list[1:]:
            if curx < prev_x:
                my_logger.debug("something gone wrong in time calculation, as cur is lower than prev")
            prev_x = curx

        if local_debug == True:
            prev_volume= volume_list[0]
            my_logger.debug("{} stock volume is {}".format(stock,prev_volume))
            for cu_volume in volume_list[1:]:
                if cu_volume < prev_volume:
                    my_logger.debug("something gone wrong in volume calculation, as cur is lower than prev")
                prev_volume = cu_volume
                my_logger.debug("{} stock volume is {}".format(stock,prev_volume))

        cur_volume_list = volume_list
        over_deamnd = (sum(buy_quantity) - sum(sell_quantity))/(sum(sell_quantity) + 1)
        over_deamnd_tiny = (sum(buy_quantity[(int)(-samples_per_decision/10):]) - sum(sell_quantity[(int)(-samples_per_decision/10):]))/(sum(sell_quantity[(int)(-samples_per_decision/10):])+1)

    #return np.array(cum_time_list), np.array(price_list),np.array(cur_volume_list), timestamp, is_possible, buy_quantity/sell_quantity
    return np.array(cum_time_list), np.array(price_list),np.array(cur_volume_list), timestamp, is_possible, over_deamnd, over_deamnd_tiny

def prep_last_prices(watch_list,data_path='E:\\kite\\history\\',load_num_samples=50,offset=-1, my_logger=None):
    
    last_prices = {}
    is_possible = False

    for stock in watch_list:
        if load_num_samples != 0:

            try:
                file = open(data_path+stock.replace(':',"_")+'_.txt', 'r')
                file_present = 1
            except Exception as e:
                file_present = 0

            if file_present == 1:
                json_data = file.read()
                lines = json_data.split("\n")
                
                if (load_num_samples <= len(lines)) and (abs(offset) <= len(lines) and ((offset+load_num_samples) <= 0)):
                
                    is_possible = True

                    if (offset + load_num_samples) == 0:
                        selected_lines = lines[offset:]
                    else:
                        selected_lines = lines[offset:offset + load_num_samples]
                else:
                    is_possible = False
                    my_logger.debug('could not read last prices of stock from file \n', stock)

                file.close()
            else:
                is_possible = False

        if is_possible == True:
            last_prices[stock] = selected_lines
            if last_prices[stock][-1] == '':
                del last_prices[stock][-1]
        else:
            last_prices[stock] = []
            
   
    return last_prices

def take_buy_sell_decision(kite,holdings,trade_book_buy,trade_book_sell,last_price,trading_session,watch_list_trading_symbol,system_time,slot_buy_amount,slot_sell_amount, buy_trigger,sell_trigger,my_logger,decay_fact=0.5,offset=-1,min_buy_amount=1000):
    
    buystock_list = []
    quant_list =[]
    price_list=[]

    # find total buy triggers
    buy_trigger_sum = 0
    sell_trigger_sum = 0
    up_stocks = 0
    down_stocks = 0

    for idx, (buy_item, sell_item) in enumerate(zip(buy_trigger,sell_trigger)):

        if idx >= 66: # small cap starts from here
            continue

        buy_trigger_sum += buy_item
        sell_trigger_sum += sell_item

        if (buy_item + sell_item) > 0.0: # if overall stat says few buys then it is good time to buy as prices would have fallen 
            up_stocks = up_stocks + 1

        if (buy_item + sell_item) < 0.0:
            down_stocks = down_stocks + 1

    up_stocks = (up_stocks+0.0001)/(up_stocks + down_stocks) # percentage of up stock is high, hence buy more frequently (no need to be matured), sell delayed (more matured)
    down_stocks = (down_stocks+0.0001)/(up_stocks + down_stocks) # percentage of down stock is high, hence buy less frequently (or more matured), sell frequently
    
    up_stocks = up_stocks + 0.2 # all are falling then up_stocks = 0.1, down_stocks ~= 0.9. so buffer to buy should be ten times higher e.g. ~10k, sell buffer ~10k
    down_stocks = down_stocks + 0.2 # all are gaining then up_stocks ~= 1.0 down_stocks = 0.1. so buffer to sell should be ten times higher e.g ~1L, and buffer to buy ~= 1k
    
    my_logger.debug("percentage of up_stocks is {} and down_stocks is {}".format(up_stocks,down_stocks))

    
    for idx, (buy_item,sell_item) in enumerate(zip(trade_book_buy,trade_book_sell)):

        if idx >= 66: # small cap starts from here
            continue

        # it is race between buy and sale, whoever reaches first will be executed first. Definitely sale is given more time than buy
        # speed of both and sell eace is same, only thing is that sell happens when too much of lag has happened.
        if buy_trigger[idx]> 0.0:
            buy_item = buy_item + slot_buy_amount*(buy_trigger[idx]/buy_trigger_sum)
            my_logger.debug("trade_book for stock {} is  moved by {} ".format( watch_list_trading_symbol[idx], slot_buy_amount*(buy_trigger[idx]/buy_trigger_sum)))                        
            my_logger.debug("buy trade_book for stock {} reached to {} ".format( watch_list_trading_symbol[idx], trade_book_buy[idx]))                                    

        if sell_trigger[idx]< 0.0:
            sell_item = sell_item - slot_buy_amount*(sell_trigger[idx]/sell_trigger_sum) # rate of buyuing and selling should be same that is why slot sell amount is not used
            my_logger.debug("trade_book for stock {} is  moved by {} ".format( watch_list_trading_symbol[idx],slot_buy_amount*(sell_trigger[idx]/sell_trigger_sum)))                        
            my_logger.debug("sell trade_book for stock {} reached to {} ".format( watch_list_trading_symbol[idx], trade_book_sell[idx]))                        

        trade_book_buy[idx] = buy_item
        trade_book_sell[idx] = sell_item

        buy_trigger[idx] = buy_trigger[idx]*decay_fact
        sell_trigger[idx] = sell_trigger[idx]*decay_fact
        
        buy_fact,sell_fact = calc_buy_sell_fact(holdings, watch_list_trading_symbol[idx])

        if(buy_item >= (buy_fact*min_buy_amount/down_stocks)):

            buystock = watch_list_trading_symbol[idx].replace('NSE:','')
            
            if (buystock == 'NIFTY 50'):
                buystock = 'NIFTYBEES'
            
            if trading_session == True:
                try:                
                    cur_price = kite.ltp('NSE:'+buystock)['NSE:'+buystock]['last_price']
                except Exception as e:                                        
                    my_logger.debug("could not get ltp for stock {} while buying".format(buystock))                
                    cur_price = 0.0

                system_time = str(time.localtime(time.time()))
            else:
                line = last_price[watch_list_trading_symbol[idx]][offset]
                json_acceptable_string = line.replace("'", "\"")
                if json_acceptable_string == '':
                    continue
                line = json.loads(json_acceptable_string)
                cur_price = (int)(line['last_price'])
                system_time =  line['timestamp']          
            
            if cur_price > 0.0:
                buy_quant = (int)(buy_item/cur_price)
            else:
                buy_quant = 0

            if buy_quant >= 1:
                buystock_list.append(buystock)
                quant_list.append(buy_quant)
                price_list.append(cur_price)

                if trading_session == True:
                    try:
                        order_id = kite.place_order(variety=kite.VARIETY_REGULAR,
                                        exchange=kite.EXCHANGE_NSE,
                                        tradingsymbol=buystock,
                                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                                        quantity=buy_quant, # buying quantatity should depend on current theta and momentum of theta
                                        product=kite.PRODUCT_CNC,
                                        order_type=kite.ORDER_TYPE_MARKET)
                        my_logger.debug("Buy Order placed for stock {} with score {} and order id {}".format(buystock,buy_trigger[idx],order_id))                                        
                        print("Buy Order placed for stock {}".format(buystock))                                        
                        trade_book_buy[idx] = trade_book_buy[idx] - buy_quant*cur_price
                        trade_book_sell[idx] = trade_book_sell[idx] + buy_quant*cur_price
                        
                        if trade_book_sell[idx] > 0:
                            trade_book_sell[idx] = 0

                        if trade_book_buy[idx] < 0:
                            trade_book_buy[idx] = 0

                        print("pending trade for stock {} is reduced to {}".format(buystock,trade_book_buy[idx]))
                        my_logger.debug("pending trade for stock {} is reduced to {}".format(buystock,trade_book_buy[idx]))
                    except Exception as e:                                        
                        my_logger.debug("Buy Order could not be placed for stock {} for buy quant {}".format(buystock,buy_quant))
                else:
                    print("Buy Order placed for stock {} {} numbers @ {} at time {}".format(buystock,buy_quant,cur_price,system_time))     
                    trade_book_buy[idx] = trade_book_buy[idx] - buy_quant*cur_price
                    print("pending trade for stock {} is reduced to {}".format(buystock,trade_book_buy[idx]))
                    my_logger.debug("pending trade for stock {} is reduced to {}".format(buystock,trade_book_buy[idx]))

        if(sell_item <= (-(min_buy_amount*sell_fact))/up_stocks):

            if watch_list_trading_symbol[idx] in not_sale_list:
                print('Avoiding the sale of stock {}'.format(watch_list_trading_symbol[idx]))
                continue
            sellstock = watch_list_trading_symbol[idx].replace('NSE:','')
            
            if (sellstock == 'NIFTY 50'):
                sellstock = 'NIFTYBEES'
            
            if trading_session == True:
                try:                
                    cur_price = kite.ltp('NSE:'+sellstock)['NSE:'+sellstock]['last_price']
                except Exception as e:                                        
                    my_logger.debug("could not get ltp for stock {} while buying".format(sellstock))                
                    cur_price = 0.0

                system_time = str(time.localtime(time.time()))
            else:
                line = last_price[watch_list_trading_symbol[idx]][offset]
                json_acceptable_string = line.replace("'", "\"")
                if json_acceptable_string == '':
                    continue
                line = json.loads(json_acceptable_string)
                cur_price = (int)(line['last_price'])
                system_time =  line['timestamp']          
            
            if cur_price > 0.0:
                sell_quant = (int)((0.0-sell_item)/cur_price)
            else:
                sell_quant = 0
            
            cur_num_stock,_ = get_num_stock(holdings,sellstock)
            sell_quant = min(cur_num_stock,sell_quant)

            if sell_quant >= 1:
                buystock_list.append(sellstock)
                quant_list.append(-sell_quant)
                price_list.append(cur_price)

                if trading_session == True:
                    try:
                        order_id = kite.place_order(variety=kite.VARIETY_REGULAR,
                                        exchange=kite.EXCHANGE_NSE,
                                        tradingsymbol=sellstock,
                                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                                        quantity=sell_quant, # buying quantatity should depend on current theta and momentum of theta
                                        product=kite.PRODUCT_CNC,
                                        order_type=kite.ORDER_TYPE_MARKET)
                        my_logger.debug("SELL Order placed for stock {} with score {}".format(sellstock,buy_trigger[idx]))                                        
                        print("SELL Order placed for stock {}".format(sellstock))         

                        trade_book_sell[idx] = trade_book_sell[idx] + sell_quant*cur_price
                        trade_book_buy[idx] = trade_book_buy[idx] - sell_quant*cur_price

                        update_num_stock(holdings,sellstock,cur_num_stock-sell_quant)

                        if trade_book_sell[idx] > 0:
                            trade_book_sell[idx] = 0

                        if trade_book_buy[idx] < 0:
                            trade_book_buy[idx] = 0

                        if cur_num_stock-sell_quant == 0: # stock is no longer avaialble in portfolio
                            trade_book_sell[idx] = 0
                            buy_trigger[idx] = 0
                            trade_book_buy[idx] = 0
                            sell_trigger[idx] = 0

                        print("pending trade for stock {} is increased to {}".format(sellstock,trade_book_sell[idx]))
                        my_logger.debug("pending trade for stock {} is increased to {}".format(sellstock,trade_book_sell[idx]))
                    except Exception as e:                                        
                        my_logger.debug("SELL Order could not be placed for stock {} for quant {}".format(sellstock,sell_quant))
                else:
                    print("SELL Order placed for stock {} {} numbers @ {} at time {}".format(sellstock,sell_quant,cur_price,system_time))     
                    
                    trade_book_sell[idx] = trade_book_sell[idx] + sell_quant*cur_price
                    trade_book_buy[idx] = trade_book_buy[idx] - sell_quant*cur_price                    

                    print("pending trade for stock {} is increased to {}".format(sellstock,trade_book_sell[idx]))
                    my_logger.debug("pending trade for stock {} is increased to {}".format(sellstock,trade_book_sell[idx]))

    return buystock_list,quant_list,price_list


def get_avg_volume_per_second_avg_price(last_prices,avg_volume,avg_price,data_path='E:\\kite\\history\\April-2022\\',max_num_days=4):

    for stock_id,stock in enumerate(last_prices):
        num_days_found = 0
        volume = 0
        price  = 0
        prev_date = 100
        hr_ref = 15
        min_ref = 00 # get the values at 3pm one
        try:
            file = open(data_path+stock.replace(':',"_")+'_.txt', 'r')
            file_present = 1
        except Exception as e:
            file_present = 0

        if file_present == 1:
            json_data = file.read()
            lines = json_data.split("\n")

            for idx in range(-1,-len(lines),-1):
                line = lines[idx]
                json_acceptable_string = line.replace("'", "\"")
                if json_acceptable_string == '':
                    continue
                line = json.loads(json_acceptable_string)
                timestamp = line['timestamp']
                yr,mnth,date = timestamp.split()[0].split('-')
                hr,min,sec = timestamp.split()[1].split(':')

                if((int(hr) >= int(hr_ref)) and (int(min) >= int(min_ref))) and (int(date) != int(prev_date)):
                    num_days_found = num_days_found + 1
                    volume = volume + int(line['volume'])
                    price = price + line['last_price']
                    prev_date = int(date)
                  
                if num_days_found >= max_num_days:
                    break
            file.close()

        if num_days_found >= 1:
            avg_volume[stock_id] = (volume/num_days_found)/22500 # 22500 is total number of seconds in 6:15 hr
            avg_price[stock_id] = price/num_days_found
        else:
            avg_volume[stock_id] = 0
                    

    return avg_volume


def total_asset_value(holdings,not_sale_list):
    total_asset = 0
    for holding in holdings: # IN DEBUG SESSION read txt files and determine holdings. 
        stock_name = holding['tradingsymbol']
        if stock_name not in  not_sale_list:
            total_asset = total_asset + holding['quantity']*holding['average_price']
    return total_asset

def total_liquid_value(holdings):
    total_asset = 0
    for holding in holdings: # IN DEBUG SESSION read txt files and determine holdings. 
        stock_name = holding['tradingsymbol']
        if stock_name == 'LIQUIDBEES':
            total_asset = total_asset + holding['quantity']*holding['average_price']
    return total_asset

def get_num_stock(holdings,stock):
    
    split_list = stock.split(':')

    if len(split_list) == 2:
        stock = split_list[1]
    
    for idx,holding in enumerate(holdings): # IN DEBUG SESSION read txt files and determine holdings. 
        stock_name = holding['tradingsymbol']
        if stock_name == stock:
            return holding['quantity'], idx
    else:
        return 0,-1

def update_num_stock(holdings,stock,quant):
    
    split_list = stock.split(':')

    if len(split_list) == 2:
        stock = split_list[1]
    
    for holding in enumerate(holdings): # IN DEBUG SESSION read txt files and determine holdings. 
        stock_name = holding['tradingsymbol']
        if stock_name == stock:
            holding['quantity'] = quant
    else:
        return 0

def calc_buy_sell_fact(holdings,buystock):
    cur_num_stock,idx = get_num_stock(holdings,buystock)
    min_fact = 0
    max_fact = 6
    if cur_num_stock > 0:
        holding = holdings[idx]
        per_gain = cur_num_stock*((holding['last_price'] - holding['average_price'])/holding['average_price'])
        
        if per_gain > 30.0:
            per_gain = 30.0
        elif per_gain<-30.0:
            per_gain = -30.0
        
        per_gain = per_gain + 30.0 # range from 0 to 60
        per_gain = per_gain /10 # range 0 to 6
        buy_fact  = max_fact - ((max_fact - min_fact)/6)*per_gain # range 10 To 0
        sell_fact = min_fact + ((max_fact - min_fact)/6)*per_gain # range 0 to 10
        buy_fact  = buy_fact + 1 # range 11 To 1
        sell_fact  = sell_fact + 4 # range 1 to 11
    else:
        buy_fact = 1
        sell_fact = 10000

    buy_fact = buy_fact + 20
    sell_fact = sell_fact + 20
    return buy_fact,sell_fact

def get_buy_sell_amount(holdings,num_stock_list):
    sell_amount = 0
    sell_amount_per_second = 0
    #sell_amount  = total_asset_value(holdings,not_sale_list)*0.005 # np.load("E:\\kite\\history\\daily\\prev_sesion_sell_gap.npy") # (total holding / 50 sessions). Means if stock falls continioulsy for 50 sessions then I should sell everything. 12Lac/50 = ~24k

    #try:
    #    file = open("E:\\kite\\history\\daily\\prev_sesion_sell_gap.npy", 'r')
    #    file_present = 1
    #    file.close()
    #except Exception as e:
    #    file_present = 0

    #if file_present==1:
    #    prev_sesion_sell_gap = np.load("E:\\kite\\history\\daily\\prev_sesion_sell_gap.npy") 
    #else:
    #    prev_sesion_sell_gap = 0
    #sell_amount = sell_amount + prev_sesion_sell_gap
    #sell_amount_per_second = (sell_amount )/22500 # 22500 is total number of seconds in 6:15 hr

    #maximum amount to buy when all stocks are raising. I have 2.5L per month, so it should get used in one month
    try:
        file = open("E:\\kite\\history\\daily\\prev_sesion_buy_gap.npy", 'r')
        file_present = 1
        file.close()
    except Exception as e:
        file_present = 0

    if file_present==1:
        prev_sesion_buy_gap = np.load("E:\\kite\\history\\daily\\prev_sesion_buy_gap.npy") 
    else:
        prev_sesion_buy_gap = 0

    allot_buy_amount = total_liquid_value(holdings)/50
    buy_amount  = allot_buy_amount + prev_sesion_buy_gap + sell_amount # only 10k can be afforded to buy each day even if all the stocks are raising
    buy_amount_per_second = buy_amount/22500 # 22500 is total number of seconds in 6:15 hr
    min_buy_amount = (buy_amount/num_stock_list)
    print("Buy {} and Sell {} amount is ".format(buy_amount,sell_amount))
    return buy_amount_per_second, sell_amount_per_second, min_buy_amount


def update_last_trade_history(watch_list_trading_symbol,trade_book_rs_buy,trade_book_rs_sell, buy_trigger, sell_trigger, holdings,my_logger):

    try:
        file = open("E:\\kite\\history\\daily\\buy_trigger.npy", 'r')
        file.close()
        file = open("E:\\kite\\history\\daily\\sell_trigger.npy", 'r')
        file.close()
        file = open("E:\\kite\\history\\daily\\trade_book_rs_buy.npy", 'r')
        file.close()
        file = open("E:\\kite\\history\\daily\\trade_book_rs_sell.npy", 'r')
        file.close()
        file = open("E:\\kite\\history\\daily\\trading_symbol.npy", 'r')
        file_present = 1
    except Exception as e:
        file_present = 0

    if file_present == 1:
        buy_trigger_prev  = np.load("E:\\kite\\history\\daily\\buy_trigger.npy")
        sell_trigger_prev  = np.load("E:\\kite\\history\\daily\\sell_trigger.npy")
        trade_book_rs_buy_prev = np.load("E:\\kite\\history\\daily\\trade_book_rs_buy.npy")
        trade_book_rs_sell_prev = np.load("E:\\kite\\history\\daily\\trade_book_rs_sell.npy")
        watch_list_trading_symbol_prev = np.load("E:\\kite\\history\\daily\\trading_symbol.npy")

        for prev_idx, stock in enumerate(watch_list_trading_symbol_prev):
            if stock in watch_list_trading_symbol:
                cur_idx = watch_list_trading_symbol.index(stock)
                trade_book_rs_buy[cur_idx] = trade_book_rs_buy_prev[prev_idx]
                trade_book_rs_sell[cur_idx] = trade_book_rs_sell_prev[prev_idx]
                buy_trigger[cur_idx] = buy_trigger_prev[prev_idx]
                sell_trigger[cur_idx] = sell_trigger_prev[prev_idx]
                print("Pending Buy trade for stock {} is {} with trigger value {} ".format(stock,trade_book_rs_buy[cur_idx],buy_trigger[cur_idx]))
                my_logger.debug("Pending Buy trade for stock {} is {} with trigger value {} ".format(stock,trade_book_rs_buy[cur_idx],buy_trigger[cur_idx]))

                print("Pending Sell trade for stock {} is {} with trigger value {} ".format(stock,trade_book_rs_sell[cur_idx],sell_trigger[cur_idx]))
                my_logger.debug("Pending Sell trade for stock {} is {} with trigger value {} ".format(stock,trade_book_rs_sell[cur_idx],sell_trigger[cur_idx]))

        for idx,stock in enumerate(watch_list_trading_symbol):
            if get_num_stock(holdings,stock)[0] == 0:
                print("No holdig for stock {} hence setting trade_book_rs_sell/sell_trigger to zero \n".format(stock))
                trade_book_rs_sell[idx] = 0
                sell_trigger[idx] = 0

