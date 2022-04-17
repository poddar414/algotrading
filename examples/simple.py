from my_apis import * 

logging.basicConfig(filename="newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w',
                    level=logging.DEBUG)

my_logger = logging.getLogger()

## Main program starts here
dump_live_quote = False
get_last_price_from_local = True
run_program = True
scannin_speed = 0
debug_print = False
per_change_th = 2.0
samples_per_decision=40
debug_time = '2022-04-08 09:15:00'
debug_iteration = 2100

slot_exec_buy_time = ['9:30', '9:40', '9:55', '10:10', '10:25', '10:40', '10:55', '11:10', '11:25', '12:00', '12:30', '13:00', '13:30', '14:00', '14:15', '14:30','14:45', '15:00', '15:14', '15:29']
#slot_exec_buy_time = ['9:40', '10:10', '10:40', '11:10', '12:00', '13:00', '14:00', '14:30', '15:00']
slot_exec_buy_flag = [False for _ in slot_exec_buy_time]

slot_exec_sell_time = ['15:00']
slot_exec_sell_flag = [False for _ in slot_exec_sell_time]

buy_amount  = 20000
sell_amount = 5000
slot_buy_amount = buy_amount/len(slot_exec_buy_time)
slot_sell_amount = sell_amount/len(slot_exec_sell_time)
trade_book = []

kite, buy_trigger, sell_trigger, watch_list_trading_symbol,trading_session,debug_session,offset = my_init(debug_time,data_path='E:\\kite\\history\\April-2022\\',samples_per_decision=samples_per_decision)

if debug_session == False:
    last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\April-2022\\',load_num_samples=samples_per_decision,offset=offset,my_logger=my_logger)
    offset = -samples_per_decision
else:
    last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\April-2022\\',load_num_samples=debug_iteration,offset=offset,my_logger=my_logger)
    offset = -debug_iteration # new offset in new subset 

while run_program == True:
    
    system_time = time.localtime(time.time())
    #print(system_time)
    # wait for market to open 
    if (((system_time.tm_hour == 9) and (system_time.tm_min >= 15)) or (system_time.tm_hour > 9)) and kite != 'NULL':
        trading_session = True
    
    # close the trading
    if (((system_time.tm_hour == 15) and (system_time.tm_min >= 30)) or(system_time.tm_hour > 15)) and (trading_session == True):
        trading_session = False
        run_program = False

    if debug_session == True or trading_session == True:
        theta_list =[]
        stock_list = []
        timestamp_list = []
        buy_sell_ratio_list = []
        for stock in watch_list_trading_symbol:
            if debug_print == True:
                print('************')
                print('Current Price ::',kite.ltp(stock))

            tics,price,timestamp, is_possible, buy_sell_ratio = sample_last_prices(last_prices[stock],samples_per_decision=samples_per_decision,offset=offset)

            if is_possible == True:
                if (tics.shape == price.shape) and (price.shape[0]>=2):
                    base_price = price[0]
                    price = np.array([x/base_price  for x in price])
                    theta = np.polyfit(tics,price,1)[0]
                    
                    theta_list.append(theta)
                    stock_list.append(stock)
                    timestamp_list.append(timestamp)
                    buy_sell_ratio_list.append(buy_sell_ratio)
                else:
                    print('something went wrong')
            else:
                theta_list.append(0.0)
                stock_list.append(stock)
                timestamp_list.append('0-0-0 0:0:0')
                buy_sell_ratio_list.append(1)
            
            if trading_session == True:
                update_last_price(last_prices,kite, stock, my_logger=my_logger)

        sort_idx = sorted(range(len(theta_list)), key=lambda k: theta_list[k])
        theta_list = [theta_list[i]*1000*1000 for i in sort_idx]
        stock_list = [stock_list[i] for i in sort_idx]
        timestamp_list = [timestamp_list[i] for i in sort_idx]
        buy_sell_ratio_list = [buy_sell_ratio_list[i] for i in sort_idx]

        my_logger.debug("One New Set")

        for stock,theta,buy_sell_ratio in zip(stock_list,theta_list,buy_sell_ratio_list):
            my_logger.debug("{} theta is {}".format(stock,theta))
            stock_idx = watch_list_trading_symbol.index(stock)
            buy_trigger[stock_idx] = buy_trigger[stock_idx] + (theta*buy_sell_ratio)
            sell_trigger[stock_idx] = sell_trigger[stock_idx] + (theta*buy_sell_ratio)

        # Buy decision
        buy_trigger,buy_stock = take_buy_decision(kite,slot_exec_buy_flag,slot_exec_buy_time,trading_session,watch_list_trading_symbol,system_time,slot_buy_amount,buy_trigger,timestamp_list,my_logger)
        
        # Sell decision
        sell_trigger = take_sell_decision(kite,slot_exec_sell_flag,slot_exec_sell_time,trading_session,watch_list_trading_symbol,system_time,slot_sell_amount,sell_trigger,timestamp_list,my_logger)

        if debug_session == True and buy_stock != '':
            json_acceptable_string = last_prices['NSE:'+buy_stock][offset].replace("'", "\"")
            line = json.loads(json_acceptable_string)

            price = line['last_price']
            quant = (int)(slot_buy_amount/price)
            if quant <= 1:
                quant = 1
            cur_buy_item = {'stock':buy_stock,'quant':quant,'price':price}
            trade_book.append(cur_buy_item)

        if debug_session == True:
            offset = offset + 1
            debug_iteration = debug_iteration - 1
            if debug_iteration == 0:
                run_program=False


        #time.sleep(1)
if (debug_session == True):
    profit = 0
    total_trade = 0
    for trade in trade_book:
        buy_stock = trade['stock']
        quant     = trade['quant']
        price     = trade['price']
        total_trade = total_trade + quant*price
        json_acceptable_string = last_prices['NSE:'+buy_stock][-1].replace("'", "\"")
        line = json.loads(json_acceptable_string)

        profit = profit + quant*(line['last_price'] - price)
    print("Total day profit is {} out of total trade of {}".format(profit,total_trade))

if (debug_session == False) and (trading_session == True):
    dump_last_prices(last_prices, watch_list_trading_symbol, samples_per_decision, data_path='E:\\kite\\history\\April-2022\\')
