import logging
from kiteconnect import KiteConnect
import time
import json
import datetime
import numpy as np

def my_init(debug_time,data_path='E:\\kite\\pykiteconnect\\history\\',samples_per_decision=40):

    trading_session = False
    
    # Check if login is required or not
    system_time = time.localtime(time.time())
    if (system_time.tm_hour >= 7) and trading_session == False and (system_time.tm_hour <= 16):
    #if False:
        kite = kite_login()
        offset = -samples_per_decision # load minimum number of samples from file # offset is assumed to be only negative
        debug_session = False
        holdings = kite.holdings()
    else:
        kite = 'NULL'
        debug_session = True
        holdings = [] 
        with open(data_path+'NSE_NIFTY 50_.txt', 'r') as file:
            json_data = file.read()
            lines = json_data.split("\n")
        file.close()
        
        yr_ref,mnth_ref,date_ref = debug_time.split()[0].split('-')
        hr_ref,min_ref,sec_ref = debug_time.split()[1].split(':')

        for offset, line in enumerate(lines):
            json_acceptable_string = line.replace("'", "\"")
            line = json.loads(json_acceptable_string)
            timestamp = line['timestamp']
            yr,mnth,date = timestamp.split()[0].split('-')
            hr,min,sec = timestamp.split()[1].split(':')
            if(((int(yr_ref) == int(yr)) and (int(mnth_ref) == int(mnth)) and (int(date_ref) == int(date))) and (int(hr) >= int(hr_ref)) and (int(min) >= int(min_ref)) and (int(sec) >= int(sec_ref))):
                break
            
        offset = offset - len(lines) # offset is assumed to be only negative

    watch_list = prep_watch_list('E:\\kite\\pykiteconnect\\watch_list.txt')
    watch_list.append({'tradingsymbol':'NSE:NIFTY 50','weight':1.0,'last_price':0.0})
    for holding in holdings: # IN DEBUG SESSION read txt files and determine holdings. 
        stock_name = holding['tradingsymbol']
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
    price_list =[]
    timestamp = '0-0-0 0:0:0'
    lines = last_prices
    # offset is assumed to be only negative
    if (samples_per_decision <= len(lines)) and (abs(offset) <= len(lines) and ((offset+samples_per_decision) <= 0)):
        
        if offset+samples_per_decision == 0:
            selected_lines = lines[offset:]    
        else:    
            selected_lines = lines[offset:offset+samples_per_decision]

        is_possible = True
    else:
        is_possible = False

    time_list = []
    price_list = []

    buy_quantity = 1
    sell_quantity = 1

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
        time_list.append(0)
        prev_time_obj = time.strptime(timestamp.split()[-1], "%H:%M:%S")
        for line in selected_lines[1:]:
            if (line != '\n') and line != '':
                json_acceptable_string = line.replace("'", "\"")
                line = json.loads(json_acceptable_string)

                timestamp = line['timestamp']
                last_price = line['last_price']
                
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
                elif cur_time_obj < prev_time_obj:
                    time_list.append(0.001)
                else:
                    time_list.append(0.001)
                #    my_logger.debug('skipping the time stamp')
                prev_time_obj = cur_time_obj

        cum_time_list = [sum(time_list[0:x:1]) for x in range(1, len(time_list)+1)]   
    return np.array(cum_time_list), np.array(price_list), timestamp, is_possible, buy_quantity/sell_quantity

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

def take_buy_decision(kite,slot_exec_flag,slot_exec_time,trading_session,watch_list_trading_symbol,system_time,slot_buy_amount,buy_trigger,timestamp_list,my_logger):
    
    buystock = ''
    
    for idx, (flag,tic) in enumerate(zip(slot_exec_flag, slot_exec_time)):
        tic_hr = (int)(tic.split(':')[0])
        tic_min = (int)(tic.split(':')[1])
        if (trading_session == True):
            if (system_time.tm_hour >= tic_hr) and (system_time.tm_min >= tic_min) and flag == False:
                slot_exec_flag[idx] = True

                my_logger.debug("Maximum theta is {}".format(np.max(buy_trigger)))

                buystock = watch_list_trading_symbol[np.where(buy_trigger == np.amax(buy_trigger))[0][0]].replace('NSE:','')
                
                if (buystock == 'NIFTY 50'):
                    buystock = 'NIFTYBEES'


                try:
                    buy_quant = slot_buy_amount/kite.ltp('NSE:'+buystock)['NSE:'+buystock]['last_price']
                    if buy_quant < 1.0:
                        buy_quant = 1
                    else:
                        buy_quant = (int)(buy_quant)
                    order_id = kite.place_order(variety=kite.VARIETY_REGULAR,
                                    exchange=kite.EXCHANGE_NSE,
                                    tradingsymbol=buystock,
                                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                                    quantity=buy_quant, # buying quantatity should depend on current theta and momentum of theta
                                    product=kite.PRODUCT_CNC,
                                    order_type=kite.ORDER_TYPE_MARKET)
                    my_logger.debug("Buy Order placed for stock {}".format(buystock))                                        
                    print("Buy Order placed for stock {}".format(buystock))                                        
                except Exception as e:                                        
                    my_logger.debug("Buy Order could not be placed for stock {}".format(buystock))
                    
                buy_trigger = buy_trigger*0.7 #once will check this after removing
                
        else:
            buy_indx = np.where(buy_trigger == np.amax(buy_trigger))[0][0]
            if ((int(timestamp_list[buy_indx].split()[1].split(":")[0])) == tic_hr) and ((int(timestamp_list[buy_indx].split()[1].split(":")[1])) == tic_min) and flag == False:
                buystock = watch_list_trading_symbol[np.where(buy_trigger == np.amax(buy_trigger))[0][0]].replace('NSE:','')
                slot_exec_flag[idx] = True
                #buy_trigger = np.zeros(len(watch_list_trading_symbol))
                buy_trigger = buy_trigger*0.7
                my_logger.debug("Buy stock {} at time {}".format(buystock,timestamp_list[buy_indx]))
                print("Buy stock {} at time {}".format(buystock,timestamp_list[buy_indx]))

    return buy_trigger,buystock


def take_sell_decision(kite,slot_exec_flag,slot_exec_time,trading_session,watch_list_trading_symbol,system_time,slot_sell_amount,sell_trigger,timestamp_list,my_logger):
    for idx, (flag,tic) in enumerate(zip(slot_exec_flag, slot_exec_time)):
        tic_hr = (int)(tic.split(':')[0])
        tic_min = (int)(tic.split(':')[1])
        if (trading_session == True):
            if (system_time.tm_hour >= tic_hr) and (system_time.tm_min >= tic_min) and flag == False:
                slot_exec_flag[idx] = True
                exchange = ''
                all_buy_index = np.where(sell_trigger >=0)
                sell_trigger[all_buy_index] = 0
                
                while exchange == '':
                    sell_index = np.where(sell_trigger == np.amin(sell_trigger))[0][0]
                    sellstock = watch_list_trading_symbol[sell_index].replace('NSE:','')

                    if (sellstock == 'NIFTY 50'):
                        sellstock = 'NIFTYBEES'

                    my_logger.debug("candidate sell stock is {}\n".format(sellstock))
                    my_logger.debug("Minimum theta is {}".format(np.min(sell_trigger)))

                    sell_trigger[sell_index] = 0
                    quantity = 1

                    for holding in kite.holdings():
                        if holding['tradingsymbol'] == sellstock:
                            exchange = holding['exchange']
                            quantity = holding['quantity']
                            my_logger.debug("Found the sell stock {} in holding \n".format(sellstock))
                            break

                    if np.sum(sell_trigger) == 0:
                        break

                if exchange == 'NSE':
                    exchange = kite.EXCHANGE_NSE
                elif exchange == 'BSE':
                    exchange = kite.EXCHANGE_BSE
                else:
                    my_logger.debug("exchange is wrong. Could not find the sell stock in holdings at all \n")

                if exchange != '':
                    sell_quant = slot_sell_amount/kite.ltp('NSE:'+sellstock)['NSE:'+sellstock]['last_price']
                    if sell_quant < 1.0:
                        sell_quant = 1
                    else:
                        sell_quant = (int)(sell_quant)
                    
                    sell_quant = min(quantity,sell_quant)

                    try: # need to check if stock is there in portfolio or not
                        order_id = kite.place_order(variety=kite.VARIETY_REGULAR,
                                        exchange=exchange,
                                        tradingsymbol=sellstock,
                                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                                        quantity=sell_quant,
                                        product=kite.PRODUCT_CNC,
                                        order_type=kite.ORDER_TYPE_MARKET)
                        my_logger.debug("Sell Order placed for stock {} on exchange {} for quantaty {}".format(sellstock,exchange,sell_quant))                                            
                    except Exception as e:                                        
                        my_logger.debug("Sell Order could not be placed for stock {} on exchange {} for quantaty {}".format(sellstock,exchange,sell_quant))                                            
                else:
                    my_logger.debug('Exchange is wrong while placing the order')

                sell_trigger = np.zeros(len(watch_list_trading_symbol)) #once will check this after removing
        else:
            sell_indx = np.where(sell_trigger == np.amin(sell_trigger))[0][0]
            if ((int(timestamp_list[sell_indx].split()[1].split(":")[0])) == tic_hr) and flag == False:
                sellstock = watch_list_trading_symbol[sell_indx].replace('NSE:','')
                slot_exec_flag[idx] = True
                sell_trigger = np.zeros(len(watch_list_trading_symbol))
                my_logger.debug("Sell stock {} at time {}".format(sellstock,timestamp_list[sell_indx]))

    return sell_trigger