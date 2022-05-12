import logging
from kiteconnect import KiteConnect
import time
import json
import datetime
import numpy as np

def my_init(debug_time,data_path='E:\\kite\\pykiteconnect\\history\\',samples_per_decision=40,consider_holdings=False,debug_session=False):

    trading_session = False
    
    # Check if login is required or not
    system_time = time.localtime(time.time())
    if (system_time.tm_hour >= 7) and trading_session == False and (system_time.tm_hour <= 16) and debug_session==False:
        kite = kite_login()
        offset = -samples_per_decision # load minimum number of samples from file # offset is assumed to be only negative
        debug_session = False
        holdings = kite.holdings()
    else:
        kite = 'NULL'
        holdings = [] 
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

    watch_list = prep_watch_list('E:\\kite\\pykiteconnect\\watch_list.txt')
    watch_list.append({'tradingsymbol':'NSE:NIFTYBEES','weight':1.0,'last_price':0.0})
    if consider_holdings == True:
        for holding in holdings: # IN DEBUG SESSION read txt files and determine holdings. 
            stock_name = holding['tradingsymbol']
            stock_name = stock_name.replace("*","")
            already_present = False
            for watch in watch_list:
                if watch['tradingsymbol'].split(':')[1] == stock_name:
                    already_present = True
            if already_present == False:
                watch_list.append({'tradingsymbol':'NSE:'+stock_name,'weight':1.0,'last_price':1.0})


    watch_list_trading_symbol=[item['tradingsymbol'] for item in watch_list]
    buy_trigger = np.zeros(len(watch_list_trading_symbol))
    sell_trigger = np.zeros(len(watch_list_trading_symbol))

    return kite, buy_trigger, sell_trigger, watch_list_trading_symbol, trading_session, debug_session,offset

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
        last_price = float(line_split[4])
        weight = float(line_split[6])
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
    if(stock != 'NSE:NIFTY 50'):
        quote[stock]['last_trade_time'] = str(quote[stock]['last_trade_time'])
    last_prices[stock].append(json.dumps(quote[stock]))     # convert dictionary to string and then append       


def sample_last_prices(last_prices,samples_per_decision=20,offset=-1):
    
    is_possible= False

    cum_time_list = []
    time_list = []

    cur_volume_list = []
    volume_list =[]

    price_list =[]
    timestamp = '0-0-0 0:0:0'
    lines = last_prices

    buy_quantity = 1
    sell_quantity = 1

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
        prev_time_obj = time.strptime(timestamp.split()[-1], "%H:%M:%S")
        day_cross_over = 0
        last_day_max_volume = 0
        for line in selected_lines[1:]:
            if (line != '\n') and line != '':
                json_acceptable_string = line.replace("'", "\"")
                line = json.loads(json_acceptable_string)

                timestamp = line['timestamp']
                last_price = line['last_price']
                volume = line['volume']
                if 'buy_quantity' in line:
                    buy_quantity = buy_quantity + line['buy_quantity']
                else:
                    buy_quantity = 1

                if 'sell_quantity' in line:
                    sell_quantity = sell_quantity + line['sell_quantity']
                else:
                    sell_quantity = 1

                price_list.append(last_price)
                cur_time_obj = time.strptime(timestamp.split()[-1], "%H:%M:%S")
                if cur_time_obj > prev_time_obj:
                    time_list.append((cur_time_obj.tm_hour - prev_time_obj.tm_hour)*60*60 + 
                    (cur_time_obj.tm_min - prev_time_obj.tm_min)*60+(cur_time_obj.tm_sec - prev_time_obj.tm_sec))

                    if (day_cross_over == 0):
                        volume_list.append(volume)
                    else:
                        volume_list.append(last_day_max_volume + volume)

                elif cur_time_obj < prev_time_obj:
                    time_list.append(0.001)
                    day_cross_over = 1
                    last_day_max_volume = volume_list[-1]
                    volume_list.append(last_day_max_volume + volume) #max(volume_list) is the last maximum volume pf previous day
                    #print('day cross over happened with previous day volume {} and fresh volume {}'.format(last_day_max_volume,volume))
                else:
                    time_list.append(0.001)
                    if (day_cross_over == 0):
                        volume_list.append(volume)
                    else:
                        volume_list.append(last_day_max_volume + volume)

                #    my_logger.debug('skipping the time stamp')
                prev_time_obj = cur_time_obj

        cum_time_list = [sum(time_list[0:x:1]) for x in range(1, len(time_list)+1)]   
        
        #prev_volume= volume_list[0]
        #for volume in volume_list:
        #    cur_volume_list.append(volume - prev_volume)
        #    prev_volume = volume
        cur_volume_list = volume_list

    return np.array(cum_time_list), np.array(price_list),np.array(cur_volume_list), timestamp, is_possible, buy_quantity/sell_quantity

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
        else:
            last_prices[stock] = []
            
   
    return last_prices

def take_buy_decision(kite,trade_book,last_price,trading_session,watch_list_trading_symbol,system_time,slot_buy_amount,buy_trigger,my_logger,decay_fact=0.5,offset=-1):
    
    buystock_list = []
    quant_list =[]
    
    # find total buy triggers
    buy_trigger_sum = 0
    for buy_item in buy_trigger:
        if buy_item > 0.0:
            buy_trigger_sum += buy_item
    
    for idx, item in enumerate(trade_book):
        
        #if buy_trigger[idx]> 0.0:
        item = item+slot_buy_amount*(buy_trigger[idx]/buy_trigger_sum)
        trade_book[idx] = item

        buy_trigger[idx] = buy_trigger[idx]*decay_fact

        my_logger.debug("trade_book for stock {} is  {} ".format( watch_list_trading_symbol[idx], trade_book[idx]))                        
        
        if(item >= 4000):

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
                buy_quant = (int)(item/cur_price)
            else:
                buy_quant = 0

            if buy_quant >= 1:
                buystock_list.append(buystock)
                quant_list.append(buy_quant)

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
                        trade_book[idx] = trade_book[idx] - buy_quant*cur_price
                        print("pending trade for stock {} is reduced to {}".format(buystock,trade_book[idx]))
                        my_logger.debug("pending trade for stock {} is reduced to {}".format(buystock,trade_book[idx]))
                    except Exception as e:                                        
                        my_logger.debug("Buy Order could not be placed for stock {}".format(buystock))
                else:
                    print("Buy Order placed for stock {} {} numbers @ {} at time {}".format(buystock,buy_quant,cur_price,system_time))     
                    trade_book[idx] = trade_book[idx] - buy_quant*cur_price
                    print("pending trade for stock {} is reduced to {}".format(buystock,trade_book[idx]))
                    my_logger.debug("pending trade for stock {} is reduced to {}".format(buystock,trade_book[idx]))

        if(item <= -20000):

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
                sell_quant = (int)((0.0-item)/cur_price)
            else:
                sell_quant = 0

            if sell_quant >= 1:
                buystock_list.append(sellstock)
                quant_list.append(-sell_quant)

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
                        trade_book[idx] = trade_book[idx] + sell_quant*cur_price
                        print("pending trade for stock {} is increased to {}".format(sellstock,trade_book[idx]))
                        my_logger.debug("pending trade for stock {} is increased to {}".format(sellstock,trade_book[idx]))
                    except Exception as e:                                        
                        my_logger.debug("SELL Order could not be placed for stock {}".format(sellstock))
                else:
                    print("SELL Order placed for stock {} {} numbers @ {} at time {}".format(sellstock,sell_quant,cur_price,system_time))     
                    trade_book[idx] = trade_book[idx] + sell_quant*cur_price
                    print("pending trade for stock {} is increased to {}".format(sellstock,trade_book[idx]))
                    my_logger.debug("pending trade for stock {} is increased to {}".format(sellstock,trade_book[idx]))

    return buystock_list,quant_list


def get_avg_volume_per_second(last_prices,avg_volume,data_path='E:\\kite\\history\\April-2022\\',max_num_days=4):

    for stock_id,stock in enumerate(last_prices):
        num_days_found = 0
        volume = 0
        prev_date = 100
        hr_ref = 15
        min_ref = 20
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
                    prev_date = int(date)
                  
                if num_days_found >= max_num_days:
                    break
            file.close()

        if num_days_found >= 1:
            avg_volume[stock_id] = (volume/num_days_found)/22500 # 22500 is total number of seconds in 6:15 hr
        else:
            avg_volume[stock_id] = 0
                    

    return avg_volume


