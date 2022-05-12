from my_apis import * 
import math
import sys

system_time = time.localtime(time.time())
log_file_name = str(system_time)+"_logfile.txt"
logging.basicConfig(filename=log_file_name,
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
samples_per_decision=140

debug_time = '2022-04-25 09:15:00'
debug_iteration = 42000
debug_session = False

buy_amount  = 40000
buy_amount_per_second = buy_amount/22500 # 22500 is total number of seconds in 6:15 hr
# 1% effect of start peak should reamin at the last of trading session
num_slots_for_buy = 22500/3 # assuming 5 sec of execution time #len(slot_exec_buy_time)

decay_fact  = math.exp((math.log(0.05)/num_slots_for_buy))

consider_holdings = True
past_data_available = True
trade_book = []
kite, buy_trigger, sell_trigger, watch_list_trading_symbol,trading_session,debug_session,offset = my_init(debug_time,data_path='E:\\kite\\history\\May-2022\\',samples_per_decision=samples_per_decision,consider_holdings=consider_holdings,debug_session=debug_session)

if debug_session == False:
    if past_data_available == True:
        last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\May-2022\\',load_num_samples=samples_per_decision,offset=offset,my_logger=my_logger)
    else:        
        last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\May-2022\\',load_num_samples=0,offset=offset,my_logger=my_logger)
        offset = -samples_per_decision
else:
    last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\May-2022\\',load_num_samples=debug_iteration,offset=offset,my_logger=my_logger)
    offset = -debug_iteration # new offset in new subset 
    debug_iteration = debug_iteration - samples_per_decision

avg_volume = np.zeros(len(watch_list_trading_symbol))
avg_volume = get_avg_volume_per_second(last_prices,avg_volume, data_path='E:\\kite\\history\\May-2022\\',max_num_days=5)
trade_book_rs = np.zeros(len(watch_list_trading_symbol))

if past_data_available == True:
    buy_trigger_prev  = np.load("buy_trigger.npy")
    trade_book_rs_prev = np.load("trade_book_rs.npy")
    watch_list_trading_symbol_prev = np.load("trading_symbol.npy")
    for prev_idx, stock in enumerate(watch_list_trading_symbol_prev):
        if stock in watch_list_trading_symbol:
            cur_idx = watch_list_trading_symbol.index(stock)
            trade_book_rs[cur_idx] = trade_book_rs_prev[prev_idx]
            buy_trigger[cur_idx] = buy_trigger_prev[prev_idx]
            print("Pending trade for stock {} is {} with trigger value {} \n".format(stock,trade_book_rs[cur_idx],buy_trigger[cur_idx]))
            my_logger.debug("Pending trade for stock {} is {} with trigger value {} \n".format(stock,trade_book_rs[cur_idx],buy_trigger[cur_idx]))

while run_program == True:
    
    system_time = time.localtime(time.time())
    #print(system_time)
    # wait for market to open 
    if (((system_time.tm_hour == 9) and (system_time.tm_min >= 15)) or (system_time.tm_hour > 9)) and kite != 'NULL':
        trading_session = True
    
    # close the trading
    if(((system_time.tm_hour == 15) and (system_time.tm_min >= 30)) or(system_time.tm_hour > 15)) and (trading_session == True):
        trading_session = False
        run_program = False

    if debug_session == True or trading_session == True:
        theta_price_list =[]
        theta_volume_list =[]
        stock_list = []
        timestamp_list = []
        buy_sell_ratio_list = []
        volume_list = []
        for idx, stock in enumerate(watch_list_trading_symbol):
            if debug_print == True:
                print('************')
                print('Current Price ::',kite.ltp(stock))

            tics, price, volume, timestamp, is_possible, buy_sell_ratio = sample_last_prices(last_prices[stock],samples_per_decision=samples_per_decision,offset=offset)

            if is_possible == True:
                if (tics.shape == price.shape) and (price.shape[0]>=2) and (tics.shape[0] >= 2) and (volume.shape[0] >= 2):
                    base_price = price[0]
                    price = np.array([x/base_price  for x in price])
                    theta_price = np.polyfit(tics,price,1)[0]
                    
                    #ticks = tics[np.where(volume>0)]
                    #volume = volume[np.where(volume>0)]

                    if (avg_volume[idx] == 0.0) and (tics[-1] != 0):
                        avg_volume[idx] = (volume[-1] - volume[0])/(tics[-1]+sys.float_info.epsilon)

                    if volume[-1] > volume[0]:
                        theta_volume  = (((volume[-1] - volume[0])/tics[-1]) - avg_volume[idx])/avg_volume[idx]
                    else:
                        theta_volume = 0 # control will come here in debug mode when day cross over happens. There assume volume as equal to average volume. However this needs to be correted
                    
                    theta_price_list.append(theta_price)
                    theta_volume_list.append(theta_volume)
                    stock_list.append(stock)
                    timestamp_list.append(timestamp)
                    buy_sell_ratio_list.append(buy_sell_ratio)
                else:
                    print('something went wrong')
            else:
                theta_price_list.append(0.0)
                theta_volume_list.append(0.0)
                stock_list.append(stock)
                timestamp_list.append('0-0-0 0:0:0')
                buy_sell_ratio_list.append(1)
            
            if trading_session == True:
                update_last_price(last_prices,kite, stock, my_logger=my_logger)

        my_logger.debug("One New Set")

        theta_volume_list = np.array([ (1.0/(1.0+math.exp((0-x)))) for x in theta_volume_list])

        for stock,theta_price,theta_volume, buy_sell_ratio in zip(stock_list,theta_price_list,theta_volume_list,buy_sell_ratio_list):
            

            stock_idx = watch_list_trading_symbol.index(stock)
            
            if buy_sell_ratio >= 2.0:
                buy_sell_ratio = 2.0
            elif buy_sell_ratio <= 0.5:
                buy_sell_ratio = 0.5

            my_logger.debug("{} theta_price is {}".format(stock,theta_price))
            my_logger.debug("{} theta_volume is {}".format(stock,theta_volume))
            my_logger.debug("{} buy_sell_ratio is {}".format(stock,buy_sell_ratio))
            my_logger.debug("{} previous score is {}".format(stock,buy_trigger[stock_idx]))

            if (theta_price >= 0.0):
                buy_trigger[stock_idx] = buy_trigger[stock_idx] + (((theta_price*(theta_volume + 0.0)))*(buy_sell_ratio))
                sell_trigger[stock_idx] = sell_trigger[stock_idx] + (((theta_price*(theta_volume+ 0.0)))*(buy_sell_ratio))
            else:
                buy_trigger[stock_idx] = buy_trigger[stock_idx] + (((theta_price*(theta_volume + 0.0)))*(1.0/buy_sell_ratio))
                sell_trigger[stock_idx] = sell_trigger[stock_idx] + (((theta_price*(theta_volume+ 0.0)))*(1.0/buy_sell_ratio))

            my_logger.debug("{} Final score is {}".format(stock,buy_trigger[stock_idx]))

        # Buy decision
        buy_stock_list,quant_list = take_buy_decision(kite,trade_book_rs,last_prices,trading_session,watch_list_trading_symbol,system_time,buy_amount_per_second*(tics[-1]/samples_per_decision),buy_trigger,my_logger,decay_fact,offset=offset)
        
        # Sell decision
        #sell_trigger = take_sell_decision(kite,slot_exec_sell_flag,slot_exec_sell_time,trading_session,watch_list_trading_symbol,system_time,slot_sell_amount,sell_trigger,timestamp_list,my_logger)

        if len(buy_stock_list) > 0:
            for idx, buy_stock in enumerate(buy_stock_list):
                json_acceptable_string = last_prices['NSE:'+buy_stock][offset].replace("'", "\"")
                line = json.loads(json_acceptable_string)

                price = line['last_price']
                quant = quant_list[idx]
                cur_buy_item = {'stock':buy_stock,'quant':quant,'price':price}
                trade_book.append(cur_buy_item)

        if debug_session == True:
            offset = offset + 1
            debug_iteration = debug_iteration - 1
            #if debug_iteration % 100 == 0:
            #     print(system_time)
            if debug_iteration == 0:
                run_program=False


        #time.sleep(1)

profit = 0
total_trade = 0
for trade in trade_book:
    buy_stock = trade['stock']
    quant     = trade['quant']
    price     = trade['price']
    total_trade = total_trade + quant*price
    json_acceptable_string = last_prices['NSE:'+buy_stock][-1].replace("'", "\"")
    line = json.loads(json_acceptable_string)
    
    if quant>0:
        profit = profit + quant*(line['last_price'] - price)
    else:
        profit = profit + (0-quant)*(price - line['last_price'])

print("Total day profit is {} out of total trade of {}".format(profit,total_trade))

if (debug_session == False):
    np.save("trading_symbol.npy",watch_list_trading_symbol)
    np.save("buy_trigger.npy",buy_trigger)
    np.save("trade_book_rs.npy",trade_book_rs)

    np.save(str(system_time) +"trading_symbol.npy",watch_list_trading_symbol)
    np.save(str(system_time) +"buy_trigger.npy",buy_trigger)
    np.save(str(system_time) +"trade_book_rs.npy",trade_book_rs)

    #dump_last_prices(last_prices, watch_list_trading_symbol, samples_per_decision, data_path='E:\\kite\\history\\April-2022\\')
    dump_last_prices(last_prices, watch_list_trading_symbol, samples_per_decision, data_path='E:\\kite\\history\\May-2022\\')
