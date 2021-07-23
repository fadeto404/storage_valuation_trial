from cmdty_storage import CmdtyStorage, RatchetInterp, three_factor_seasonal_value
import pandas as pd

storage_with_ratchets = CmdtyStorage(
    freq='D',
    storage_start = '2021-04-01',
    storage_end = '2022-04-01',
    injection_cost = 0.01,
    withdrawal_cost = 0.025,
    ratchets = [
                ('2021-04-01', # For days after 2021-04-01 (inclusive) until 2022-10-01 (exclusive):
                       [
                            (0.0, -150.0, 250.0),    # At min inventory of zero, max withdrawal of 150, max injection 250
                            (2000.0, -200.0, 175.0), # At inventory of 2000, max withdrawal of 200, max injection 175
                            (5000.0, -260.0, 155.0), # At inventory of 5000, max withdrawal of 260, max injection 155
                            (7000.0, -275.0, 132.0), # At max inventory of 7000, max withdrawal of 275, max injection 132
                        ]),
                  ('2022-10-01', # For days after 2022-10-01 (inclusive):
                       [
                            (0.0, -130.0, 260.0),    # At min inventory of zero, max withdrawal of 130, max injection 260
                            (2000.0, -190.0, 190.0), # At inventory of 2000, max withdrawal of 190, max injection 190
                            (5000.0, -230.0, 165.0), # At inventory of 5000, max withdrawal of 230, max injection 165
                            (7000.0, -245.0, 148.0), # At max inventory of 7000, max withdrawal of 245, max injection 148
                        ]),
                 ],
    ratchet_interp = RatchetInterp.LINEAR
)


# Creating the Inputs
monthly_index = pd.period_range(start='2021-04-25', periods=25, freq='M')
monthly_fwd_prices = [16.61, 15.68, 15.42, 15.31, 15.27, 15.13, 15.96, 17.22, 17.32, 17.66, 
                      17.59, 16.81, 15.36, 14.49, 14.28, 14.25, 14.32, 14.33, 15.30, 16.58, 
                      16.64, 16.79, 16.64, 15.90, 14.63]
fwd_curve = pd.Series(data=monthly_fwd_prices, index=monthly_index).resample('D').fillna('pad')

rates = [0.005, 0.006, 0.0072, 0.0087, 0.0101, 0.0115, 0.0126]
rates_pillars = pd.PeriodIndex(freq='D', data=['2021-04-25', '2021-06-01', '2021-08-01', '2021-12-01', '2022-04-01', 
                                              '2022-12-01', '2023-12-01'])
ir_curve = pd.Series(data=rates, index=rates_pillars).resample('D').asfreq('D').interpolate(method='linear')

def settlement_rule(delivery_date):
    return delivery_date.asfreq('M').asfreq('D', 'end') + 20

# Call the three-factor seasonal model
three_factor_results = three_factor_seasonal_value(
    cmdty_storage = storage_with_ratchets,
    val_date = '2021-04-25',
    inventory = 1500.0,
    fwd_curve = fwd_curve,
    interest_rates = ir_curve,
    settlement_rule = settlement_rule,
    num_sims = 2000,
    seed = 12,
    spot_mean_reversion = 91.0,
    spot_vol = 0.85,
    long_term_vol =  0.30,
    seasonal_vol = 0.19,
    basis_funcs = '1 + x_st + x_sw + x_lt + s + x_st**2 + x_sw**2 + x_lt**2 + s**2 + s * x_st',
    discount_deltas = True
)

# Inspect the NPV results
print('Full NPV:\t{0:,.0f}'.format(three_factor_results.npv))
print('Intrinsic NPV: \t{0:,.0f}'.format(three_factor_results.intrinsic_npv))
print('Extrinsic NPV: \t{0:,.0f}'.format(three_factor_results.extrinsic_npv))

ax_triggers = three_factor_results.trigger_prices['inject_trigger_price'].plot(
    title='Trigger Prices vs Forward Curve', legend=True)
three_factor_results.trigger_prices['withdraw_trigger_price'].plot(legend=True)
fwd_curve['2021-04-25' : '2022-04-01'].plot(legend=True)
ax_triggers.legend(['Inject Trigger Price', 'Withdraw Trigger', 'Forward Curve'])

three_factor_results.deltas.plot(title='Deltas')


# Multifactor model
# Parameters for a constant volatility 2-factor model
long_term_vol = 0.14
long_term_mean_reversion = 0.0
short_term_vol = 0.64
short_term_mean_reversion = 16.2

# Construct the factors argument of multi_factor_value function
factor_index = pd.period_range(start=val_date, end=storage.end, freq=storage.freq)
long_term_vol_curve = pd.Series(index=factor_index, dtype='float64')
long_term_vol_curve[:] = long_term_vol

short_term_vol_curve = pd.Series(index=factor_index, dtype='float64')
short_term_vol_curve[:] = short_term_vol

factors = [(short_term_mean_reversion, short_term_vol_curve),
          (long_term_mean_reversion, short_term_vol_curve)]

factor_corrs = 0.64
factor_corrs_matrix = np.array([[1.0, factor_corrs], 
                                [factor_corrs, 1.0]])
multi_factor_basis_funcs = '1 + x0 + x1 + s + x0**2 + x1**2 + s**2 + x0*x1 + x1*s + x0*s'

multi_factor_results = multi_factor_value(
    cmdty_storage = storage,
    val_date = '2021-04-25',
    inventory = 1500.0,
    fwd_curve = fwd_curve,
    interest_rates = ir_curve,
    settlement_rule = settlement_rule,
    discount_deltas=discount_deltas,
    num_sims = num_sims,
    seed = seed,
    fwd_sim_seed = fwd_sim_seed,
    factors = factors,
    factor_corrs = factor_corrs_matrix,
    basis_funcs = multi_factor_basis_funcs
)
'{0:,.0f}'.format(multi_factor_results.npv)









