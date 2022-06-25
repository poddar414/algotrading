import numpy as np
import matplotlib.pyplot as plt
import math

log_file = "E:\kite\history\daily\debug.txt"

with open(log_file, 'r') as file:
    lines = file.readlines()
file.close()
search_strings = ['NSE:POLYPLEX theta_price', 'NSE:POLYPLEX Final score is', 'trade_book for stock NSE:POLYPLEX reached to']
label_name = ['theta_price','final_score', 'trade_book']

data = [[] for _ in search_strings]

for line in lines:
    for idx, search_string in enumerate(search_strings):
        split_lines = line.split(search_string)
        if len(split_lines) > 1:
            right_part = split_lines[1]
            val_list = right_part.split(' ')
            for val in val_list:
                if val != '':
                    try:
                        float_val = float(val)
                        data[idx].append(float_val)
                        break
                    except Exception as e:
                        continue

                    

min_length = 10000000000
normalize_data= True
for idx, cur_data in enumerate(data):
    if normalize_data == True:
        cur_max = max(data[idx])
        cur_min = min(data[idx])
        mean = sum(data[idx])/len(cur_data)
        scale = (cur_max-cur_min)
        data[idx] =[(_data_ - mean)/scale for _data_ in data[idx]]
        label_name[idx] = label_name[idx] +"_mean" + "{:.2f}".format(mean) + '_scale_' + "{:.2f}".format(cur_max-cur_min) 
    if min_length > len(data[idx]):
        min_length = len(data[idx])

x = range(min_length)

for idx, _ in enumerate(search_strings):
    y = data[idx]
    plt.plot(x, y[:min_length],label = label_name[idx])

plt.legend(loc='best')
plt.show()
input()

