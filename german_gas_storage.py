from cmdty_storage import CmdtyStorage, three_factor_seasonal_value
from matplotlib import pyplot as plt

import pandas as pd
import numpy as np


NUM_STORAGE_FACILITIES = 4
DATA_LAG = 0

def perform_valuation():
    german_gas_storage_sets = list()
    gas_storage_facilities = list()
    
    # Load the 4 datasets about German storage facilities
    for i in range(0, NUM_STORAGE_FACILITIES):
        german_gas_storage_sets.append(pd.read_excel('data/Combined-2021-07-22-2021-06-22.xlsx', i))
        
        # Create storage object for each facility
        gas_storage_facilities.append(CmdtyStorage(freq='H', 
                                               storage_start = german_gas_storage_sets[i]['GAS DAY STARTED ON'][DATA_LAG], 
                                               storage_end = '2022-07-21', 
                                               injection_cost = 0.01, 
                                               withdrawal_cost = 0.02,
                                               min_inventory = 0,
                                               max_inventory = convert_twh_mmbtu(german_gas_storage_sets[i]['WORKING GAS VOLUME(TWh)'][DATA_LAG]),  # Latest working volume
                                               max_injection_rate = convert_gwh_mmbtu(german_gas_storage_sets[i]['INJECTION CAPACITY(GWh/d)'][DATA_LAG]) / 24,
                                               max_withdrawal_rate = convert_gwh_mmbtu(german_gas_storage_sets[i]['WITHDRAWAL CAPACITY(GWh/d)'][DATA_LAG]) / 24,
                                               )
                                  )


    begin_date = '2021-07-21'
    
    # Creating the Inputs
    monthly_index = pd.period_range(start=begin_date, periods=25, freq='M')
    monthly_fwd_prices = [16.61, 15.68, 15.42, 15.31, 15.27, 15.13, 15.96, 17.22, 17.32, 17.66, 
                          17.59, 16.81, 15.36, 14.49, 14.28, 14.25, 14.32, 14.33, 15.30, 16.58, 
                          16.64, 16.79, 16.64, 15.90, 14.63]
    
    # Resamples the forward curve and uses piecewise linear interpolation to fill missing values
    fwd_curve = pd.Series(data=monthly_fwd_prices, index=monthly_index).resample('H').interpolate('linear')
    fwd_curve.plot(title='Forward curve')
    
    int_rates = [0.005, 0.006, 0.0072, 0.0087, 0.0101, 0.0115, 0.0126]
    int_rates_pillars = pd.PeriodIndex(freq='D', data=['2021-07-21', '2021-08-01', '2021-12-01', '2022-04-01', 
                                                  '2022-12-01', '2023-12-01', '2024-04-01'])
    ir_curve = pd.Series(data=int_rates, index=int_rates_pillars).resample('D').asfreq('D').interpolate(method='linear').fillna('pad')
    
    def settlement_rule(delivery_date):
        return (delivery_date.asfreq('M').asfreq('D', 'end') + 20)
    
    # Call the three-factor seasonal model for each storage facility
    for i in range(0, len(gas_storage_facilities)):
        three_factor_results = three_factor_seasonal_value(
            cmdty_storage = gas_storage_facilities[i],
            val_date = begin_date,
            inventory = convert_twh_mmbtu(german_gas_storage_sets[i]['GAS IN STORAGE(TWh)'][DATA_LAG]),
            fwd_curve = fwd_curve,
            interest_rates = ir_curve,
            settlement_rule = settlement_rule,
            num_sims = 20000,
            seed = 12,
            spot_mean_reversion = 91.0,
            spot_vol = 0.85,
            long_term_vol =  0.30,
            seasonal_vol = 0.19,
            basis_funcs = '1 + x_st + x_sw + x_lt + s + x_st**2 + x_sw**2 + x_lt**2 + s**2 + s * x_st',
            discount_deltas = True,
            numerical_tolerance=1E-5
        )
    
    # Inspect the NPV results
    print('Full NPV:\t{0:,.0f}'.format(three_factor_results.npv))
    print('Intrinsic NPV: \t{0:,.0f}'.format(three_factor_results.intrinsic_npv))
    print('Extrinsic NPV: \t{0:,.0f}'.format(three_factor_results.extrinsic_npv))
    
    
    

################# UTILITY FUNCTIONS #################

def convert_twh_mmbtu(twh):
    return  3412141.6331279*twh

def convert_gwh_mmbtu(gwh):
    return 3412.1416331*gwh


if __name__ == '__main__':
    perform_valuation()
