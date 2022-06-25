from my_apis import * 
import math
import sys

system_time = time.localtime(time.time())
log_file_name = str(system_time)+"_logfile.txt"
log_file_name = 'E:\\kite\\history\\daily\\'+log_file_name
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
samples_per_decision=400

debug_time = '2022-06-08 09:25:00'
debug_iteration = 5500
debug_session = False

consider_holdings = False
past_data_available = True
trade_book = []

kite, buy_trigger, sell_trigger, watch_list_trading_symbol,trading_session,debug_session,offset, holdings = my_init(debug_time,data_path='E:\\kite\\history\\June-2022\\',samples_per_decision=samples_per_decision,consider_holdings=consider_holdings,debug_session=debug_session)

# maximum amount to sell when all stocks are falling
buy_amount_per_second , sell_amount_per_second, min_buy_amount = get_buy_sell_amount(holdings,len(watch_list_trading_symbol))
# 50% effect of start peak should reamin at the last of trading session
exec_secs =10
num_slots_for_buy = 22500/exec_secs # assuming 5 sec of execution time #len(slot_exec_buy_time)

decay_fact  = math.exp((math.log(0.5)/num_slots_for_buy))

if debug_session == False:
    if past_data_available == True:
    #if False:
        last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\June-2022\\',load_num_samples=samples_per_decision,offset=offset,my_logger=my_logger)
    else:        
        last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\June-2022\\',load_num_samples=0,offset=offset,my_logger=my_logger)
        offset = -samples_per_decision
else:
    last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\history\\June-2022\\',load_num_samples=debug_iteration,offset=offset,my_logger=my_logger)
    offset = -debug_iteration # new offset in new subset 
    debug_iteration = debug_iteration - samples_per_decision

avg_volume = np.zeros(len(watch_list_trading_symbol))
avg_price = np.zeros(len(watch_list_trading_symbol))
avg_volume = get_avg_volume_per_second_avg_price(last_prices,avg_volume,avg_price, data_path='E:\\kite\\history\\June-2022\\',max_num_days=5)

trade_book_rs_buy = np.zeros(len(watch_list_trading_symbol))
trade_book_rs_sell = np.zeros(len(watch_list_trading_symbol))

if (past_data_available == True) and (debug_session == False):
    update_last_trade_history(watch_list_trading_symbol,trade_book_rs_buy,trade_book_rs_sell,buy_trigger,sell_trigger,holdings,my_logger)

while run_program == True:
    
    system_time = time.localtime(time.time())
    #print(system_time)
    # wait for market to open 
    if (((system_time.tm_hour == 9) and (system_time.tm_min >= 15)) or (system_time.tm_hour > 9)) and kite != 'NULL':
        trading_session = True
    
    # close the trading
    if(((system_time.tm_hour == 15) and (system_time.tm_min >= 14)) or(system_time.tm_hour > 15)) and (trading_session == True):
        trading_session = False
        run_program = False

    if debug_session == True or trading_session == True:
        theta_price_list =[]
        theta_volume_list =[]
        stock_list = []
        timestamp_list = []
        buy_sell_ratio_list = []
        volume_list = []
        avg_price_scale_list =[]
        system_time_a = time.localtime(time.time())
        all_possible=True
        for idx, stock in enumerate(watch_list_trading_symbol):
            if debug_print == True:
                print('************')
                print('Current Price ::',kite.ltp(stock))

            tics, price, volume, timestamp, is_possible, buy_sell_ratio = sample_last_prices(last_prices[stock],stock,samples_per_decision=samples_per_decision,offset=offset,my_logger=my_logger)
            
            if is_possible == True:
                if (tics.shape == price.shape) and (price.shape[0]>=2) and (tics.shape[0] >= 2) and (volume.shape[0] >= 2):
                    base_price = price[0]

                    if (avg_price[idx] == 0.0):
                        avg_price[idx] = base_price

                    price = np.array([x/base_price  for x in price])
                    theta_price = np.polyfit(tics,price,1)[0]
                    
                    #ticks = tics[np.where(volume>0)]
                    #volume = volume[np.where(volume>0)]

                    if (avg_volume[idx] == 0.0) and (tics[-1] != 0):
                        avg_volume[idx] = (volume[-1] - volume[0])/(tics[-1]+sys.float_info.epsilon)
                        my_logger.debug("{} stock average volume is calculated as {} ".format(stock,avg_volume[idx]))                        

                    if volume[-1] > volume[0]:
                        theta_volume  = (((volume[-1] - volume[0])/tics[-1]) - avg_volume[idx])/avg_volume[idx]
                    else:
                        theta_volume = 0 # control will come here in debug mode when day cross over happens. There assume volume as equal to average volume. However this needs to be correted
                        my_logger.debug("{} stock last volume is not > than previous one".format(stock))                                                
                    my_logger.debug("{} stock theta volume is {} ".format(stock,theta_volume))                        
                    
                    theta_price_list.append(theta_price)
                    theta_volume_list.append(theta_volume)
                    stock_list.append(stock)
                    timestamp_list.append(timestamp)
                    buy_sell_ratio_list.append(buy_sell_ratio)
                    avg_price_scale_list.append(base_price/avg_price[idx])
                else:
                    print('something went wrong')
            else:
                theta_price_list.append(0.0) # important to have theta value zero so that score doesnt change
                theta_volume_list.append(1.0)
                stock_list.append(stock)
                timestamp_list.append('0-0-0 0:0:0')
                buy_sell_ratio_list.append(1.0)
                avg_price_scale_list.append(1.0)
                all_possible = False
            
            if trading_session == True:
                update_last_price(last_prices,kite, stock, my_logger=my_logger)
            else:
                selected_lines = last_prices[stock][offset+samples_per_decision]
                json_acceptable_string = selected_lines.replace("'", "\"")
                line = json.loads(json_acceptable_string)

                timestamp = line['timestamp']
                last_price = line['last_price']

                my_logger.debug("{} stock Ltp is {} ".format(stock,last_price))
                my_logger.debug("{} stock timestamp is {} ".format(stock,timestamp))                

        theta_volume_list = np.array([ (1.0/(1.0+math.exp((0-x)))) for x in theta_volume_list])

        for stock,theta_price,theta_volume, buy_sell_ratio,avg_price_scale in zip(stock_list,theta_price_list,theta_volume_list,buy_sell_ratio_list,avg_price_scale_list):
            

            stock_idx = watch_list_trading_symbol.index(stock)
            
            if buy_sell_ratio >= 2.0:
                buy_sell_ratio = 2.0
            elif buy_sell_ratio <= 0.5:
                buy_sell_ratio = 0.5

            my_logger.debug("{} theta_price is {}".format(stock,theta_price))
            my_logger.debug("{} theta_volume is {}".format(stock,theta_volume))
            my_logger.debug("{} buy_sell_ratio is {}".format(stock,buy_sell_ratio))
            prev_score = buy_trigger[stock_idx]

            if (theta_price >= 0.0):
                buy_trigger[stock_idx] = buy_trigger[stock_idx] + (((theta_price*(theta_volume + 0.0)))*(buy_sell_ratio)*avg_price_scale)
                sell_trigger[stock_idx] = sell_trigger[stock_idx] + (((theta_price*(theta_volume+ 0.0)))*(buy_sell_ratio)*avg_price_scale)
                #buy_trigger[stock_idx] = (((theta_price*(theta_volume + 0.0)))*(buy_sell_ratio)*avg_price_scale)

            else:
                buy_trigger[stock_idx] = buy_trigger[stock_idx] + (((theta_price*(theta_volume + 0.0)))*(1.0/buy_sell_ratio)*(1.0/avg_price_scale))
                sell_trigger[stock_idx] = sell_trigger[stock_idx] + (((theta_price*(theta_volume+ 0.0)))*(1.0/buy_sell_ratio)*(1.0/avg_price_scale))
                #buy_trigger[stock_idx] = (((theta_price*(theta_volume + 0.0)))*(1.0/buy_sell_ratio)*(1.0/avg_price_scale))

            if buy_trigger[stock_idx] < 0:
                buy_trigger[stock_idx] = 0

            if sell_trigger[stock_idx] > 0:
                sell_trigger[stock_idx] = 0

            my_logger.debug("{} score changed by {}".format(stock,(buy_trigger[stock_idx]-prev_score)))
            my_logger.debug("{} Final score is {}".format(stock,buy_trigger[stock_idx]))

        # Buy decision
        if all_possible == True: # Start only when all_possible
            buy_stock_list,quant_list,price_list = take_buy_sell_decision(kite,holdings,trade_book_rs_buy,trade_book_rs_sell,last_prices,trading_session,watch_list_trading_symbol,system_time,buy_amount_per_second*(tics[-1]/samples_per_decision),sell_amount_per_second*(tics[-1]/samples_per_decision), buy_trigger, sell_trigger,my_logger,decay_fact=decay_fact,offset=offset,min_buy_amount=min_buy_amount)
        
            if len(buy_stock_list) > 0:
                for idx, buy_stock in enumerate(buy_stock_list):
                    price = price_list[idx]
                    quant = quant_list[idx]
                    cur_buy_item = {'stock':buy_stock,'quant':quant,'price':price}
                    print(cur_buy_item)
                    trade_book.append(cur_buy_item)

            if debug_session == True:
                offset = offset + 1
                debug_iteration = debug_iteration - 1
                #if debug_iteration % 100 == 0:
                #     print(system_time)
                if debug_iteration == 0:
                    run_program=False

        system_time_b = time.localtime(time.time())
        exec_secs = ((time.mktime(system_time_b) - time.mktime(system_time_a)+0.0001))
        num_slots_for_buy = 22500/exec_secs #N
        decay_fact  = math.exp((math.log(0.5)/num_slots_for_buy)) # decay_fact^N = 0.5
        my_logger.debug("Execution time is {} ".format((time.mktime(system_time_b) - time.mktime(system_time_a))))                        
        #time.sleep(1)

profit = 0
total_trade = 0
total_buy_amount = 0
total_sell_amount = 0
for trade in trade_book:
    buy_stock = trade['stock']
    quant     = trade['quant']
    price     = trade['price']
    total_trade = total_trade + quant*price
    json_acceptable_string = last_prices['NSE:'+buy_stock][-1].replace("'", "\"")
    line = json.loads(json_acceptable_string)
    
    if quant>0:
        profit = profit + quant*(line['last_price'] - price)
        total_buy_amount =  total_buy_amount + trade['quant']*trade['price']
    else:
        profit = profit + (0-quant)*(price - line['last_price'])
        total_sell_amount = total_sell_amount + trade['quant']*trade['price']

print("Total day profit is {} out of total trade of {}".format(profit,total_trade))
prev_sesion_buy_gap = buy_amount_per_second*22500 - total_buy_amount
prev_sesion_sell_gap = sell_amount_per_second*22500 + total_sell_amount

if (debug_session == False):
    np.save("E:\\kite\\history\\daily\\trading_symbol.npy",watch_list_trading_symbol)
    np.save("E:\\kite\\history\\daily\\buy_trigger.npy",buy_trigger)
    np.save("E:\\kite\\history\\daily\\sell_trigger.npy",sell_trigger)
    np.save("E:\\kite\\history\\daily\\trade_book_rs_buy.npy",trade_book_rs_buy)
    np.save("E:\\kite\\history\\daily\\trade_book_rs_sell.npy",trade_book_rs_sell)
    np.save("E:\\kite\\history\\daily\\prev_sesion_buy_gap.npy",prev_sesion_buy_gap)
    np.save("E:\\kite\\history\\daily\\prev_sesion_sell_gap.npy",prev_sesion_sell_gap)

    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"trading_symbol.npy",watch_list_trading_symbol)
    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"buy_trigger.npy",buy_trigger)
    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"sell_trigger.npy",sell_trigger)
    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"trade_book_rs_buy.npy",trade_book_rs_buy)
    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"trade_book_rs_sell.npy",trade_book_rs_sell)    
    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"prev_sesion_buy_gap.npy",prev_sesion_buy_gap)
    np.save("E:\\kite\\history\\daily\\" + str(system_time) +"prev_sesion_sell_gap.npy",prev_sesion_sell_gap)

    #dump_last_prices(last_prices, watch_list_trading_symbol, samples_per_decision, data_path='E:\\kite\\history\\May-2022\\')
    dump_last_prices(last_prices, watch_list_trading_symbol, samples_per_decision, data_path='E:\\kite\\history\\June-2022\\')
    holdings = kite.holdings()
    with open('E:\\kite\\history\\daily\\holdings.json', 'w') as f:
        json.dump(holdings, f)        

