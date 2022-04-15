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
debug_iteration = 2000

#slot_exec_buy_time = ['9:25', '9:40', '9:55', '10:10', '10:25', '10:40', '10:55', '11:10', '11:25', '12:00', '12:30', '13:00', '13:30', '14:00', '14:15', '14:30','14:45', '15:00', '15:14', '15:29']
slot_exec_buy_time = ['9:40', '10:10', '10:40', '11:10', '12:00', '13:00', '14:00', '14:30', '15:00']
slot_exec_buy_flag = [False for _ in slot_exec_buy_time]

slot_exec_sell_time = ['15:00']
slot_exec_sell_flag = [False for _ in slot_exec_sell_time]

buy_amount  = 20000
sell_amount = 5000
slot_buy_amount = buy_amount/len(slot_exec_buy_time)
slot_sell_amount = sell_amount/len(slot_exec_sell_time)

kite, buy_trigger, sell_trigger, watch_list_trading_symbol,trading_session,debug_session,offset = my_init(debug_time,data_path='E:\\kite\\pykiteconnect\\history\\April-2022\\')
last_prices = prep_last_prices(watch_list_trading_symbol,data_path='E:\\kite\\pykiteconnect\\history\\April-2022\\',samples_per_decision=0,offset=offset,my_logger=my_logger)

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
        for stock in watch_list_trading_symbol:
            if debug_print == True:
                print('************')
                print('Current Price ::',kite.ltp(stock))

            tics,price,timestamp, is_possible = sample_last_prices(last_prices[stock],samples_per_decision=samples_per_decision,offset=offset)

            if is_possible == True:
                if tics.shape == price.shape:
                    base_price = price[0]
                    price = np.array([x/base_price  for x in price])
                    theta = np.polyfit(tics,price,1)[0]
                    
                    theta_list.append(theta)
                    stock_list.append(stock)
                    timestamp_list.append(timestamp)
                else:
                    print('something went wrong')
            else:
                theta_list.append(0.0)
                stock_list.append(stock)
                timestamp_list.append('0-0-0 0:0:0')

            update_last_price(last_prices,kite, stock, trading_session, debug_session,offset=offset + samples_per_decision,my_logger=my_logger)

        if debug_session == True:
            offset = offset + 1 # only used in debug mode
            debug_iteration = debug_iteration - 1
            if debug_iteration == 0:
                run_program=False

        sort_idx = sorted(range(len(theta_list)), key=lambda k: theta_list[k])
        theta_list = [theta_list[i]*1000*1000 for i in sort_idx]
        stock_list = [stock_list[i] for i in sort_idx]
        timestamp_list = [timestamp_list[i] for i in sort_idx]

        my_logger.debug("One New Set")

        for stock,theta in zip(stock_list,theta_list):
            my_logger.debug("{} theta is {}".format(stock,theta))
            buy_trigger[watch_list_trading_symbol.index(stock)] = buy_trigger[watch_list_trading_symbol.index(stock)] + theta
            sell_trigger[watch_list_trading_symbol.index(stock)] = sell_trigger[watch_list_trading_symbol.index(stock)] + theta

        # Buy decision
        buy_trigger = take_buy_decision(kite,slot_exec_buy_flag,slot_exec_buy_time,trading_session,watch_list_trading_symbol,system_time,slot_buy_amount,buy_trigger,timestamp_list,my_logger)

        # Sell decision
        sell_trigger = take_sell_decision(kite,slot_exec_sell_flag,slot_exec_sell_time,trading_session,watch_list_trading_symbol,system_time,slot_sell_amount,sell_trigger,timestamp_list,my_logger)

        #time.sleep(1)

if (debug_session == False) and (trading_session == True):
    dump_last_prices(last_prices, watch_list_trading_symbol, samples_per_decision, data_path='E:\\kite\\pykiteconnect\\history\\April-2022\\')
