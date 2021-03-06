"""NO LONGER USED. SEE neurokit2_parallel.py
"""
import re

import joblib
import neurokit2 as nk
import numpy as np
import pandas as pd
import scipy as sp
from tsfresh import extract_features
import wfdb

from util import convert_to_wfdb_record


IR_COLS = [
    "ECG_Rate_Mean",
    "HRV_RMSSD",
    "HRV_MeanNN",
    "HRV_SDNN",
    "HRV_SDSD",
    "HRV_CVNN",
    "HRV_CVSD",
    "HRV_MedianNN",
    "HRV_MadNN",
    "HRV_MCVNN",
    "HRV_IQRNN",
    "HRV_pNN50",
    "HRV_pNN20",
    "HRV_TINN",
    "HRV_HTI",
    "HRV_ULF",
    "HRV_VLF",
    "HRV_LF",
    "HRV_HF",
    "HRV_VHF",
    "HRV_LFHF",
    "HRV_LFn",
    "HRV_HFn",
    "HRV_LnHF",
    "HRV_SD1",
    "HRV_SD2",
    "HRV_SD1SD2",
    "HRV_S",
    "HRV_CSI",
    "HRV_CVI",
    "HRV_CSI_Modified",
    "HRV_PIP",
    "HRV_IALS",
    "HRV_PSS",
    "HRV_PAS",
    "HRV_GI",
    "HRV_SI",
    "HRV_AI",
    "HRV_PI",
    "HRV_C1d",
    "HRV_C1a",
    "HRV_SD1d",
    "HRV_SD1a",
    "HRV_C2d",
    "HRV_C2a",
    "HRV_SD2d",
    "HRV_SD2a",
    "HRV_Cd",
    "HRV_Ca",
    "HRV_SDNNd",
    "HRV_SDNNa",
    "HRV_ApEn",
    "HRV_SampEn",
]

"""
NOTE: Not all of these metrics are outputted. Taken from the Neurokit2 lib docstrings

- *"ECG_Rate_Mean"*: the mean heart rate.
Time Domain HRV metrics:
    - **HRV_RMSSD**: The square root of the mean of the sum of successive differences between
    adjacent RR intervals. It is equivalent (although on another scale) to SD1, and
    therefore it is redundant to report correlations with both (Ciccone, 2017).
    - **HRV_MeanNN**: The mean of the RR intervals.
    - **HRV_SDNN**: The standard deviation of the RR intervals.
    - **HRV_SDSD**: The standard deviation of the successive differences between RR intervals.
    - **HRV_CVNN**: The standard deviation of the RR intervals (SDNN) divided by the mean of the RR
    intervals (MeanNN).
    - **HRV_CVSD**: The root mean square of the sum of successive differences (RMSSD) divided by the
    mean of the RR intervals (MeanNN).
    - **HRV_MedianNN**: The median of the absolute values of the successive differences between RR intervals.
    - **HRV_MadNN**: The median absolute deviation of the RR intervals.
    - **HRV_HCVNN**: The median absolute deviation of the RR intervals (MadNN) divided by the median
    of the absolute differences of their successive differences (MedianNN).
    - **HRV_IQRNN**: The interquartile range (IQR) of the RR intervals.
    - **HRV_pNN50**: The proportion of RR intervals greater than 50ms, out of the total number of RR intervals.
    - **HRV_pNN20**: The proportion of RR intervals greater than 20ms, out of the total number of RR intervals.
    - **HRV_TINN**: A geometrical parameter of the HRV, or more specifically, the baseline width of
    the RR intervals distribution obtained by triangular interpolation, where the error of least
    squares determines the triangle. It is an approximation of the RR interval distribution.
    - **HRV_HTI**: The HRV triangular index, measuring the total number of RR intervals divded by the
    height of the RR intervals histogram.

Frequency Domain HRV metrics:
    - **HRV_ULF**: The spectral power density pertaining to ultra low frequency band i.e., .0 to .0033 Hz
    by default.
    - **HRV_VLF**: The spectral power density pertaining to very low frequency band i.e., .0033 to .04 Hz
    by default.
    - **HRV_LF**: The spectral power density pertaining to low frequency band i.e., .04 to .15 Hz by default.
    - **HRV_HF**: The spectral power density pertaining to high frequency band i.e., .15 to .4 Hz by default.
    - **HRV_VHF**: The variability, or signal power, in very high frequency i.e., .4 to .5 Hz by default.
    - **HRV_LFn**: The normalized low frequency, obtained by dividing the low frequency power by
    the total power.
    - **HRV_HFn**: The normalized high frequency, obtained by dividing the low frequency power by
    the total power.
    - **HRV_LnHF**: The log transformed HF.

Non-linear HRV metrics:
- **Characteristics of the Poincaré Plot Geometry**:
    - **HRV_SD1**: SD1 is a measure of the spread of RR intervals on the Poincaré plot
    perpendicular to the line of identity. It is an index of short-term RR interval
    fluctuations, i.e., beat-to-beat variability. It is equivalent (although on another
    scale) to RMSSD, and therefore it is redundant to report correlations with both
    (Ciccone, 2017).
    - **HRV_SD2**: SD2 is a measure of the spread of RR intervals on the Poincaré plot along the
    line of identity. It is an index of long-term RR interval fluctuations.
    - **HRV_SD1SD2**: the ratio between short and long term fluctuations of the RR intervals
    (SD1 divided by SD2).
    - **HRV_S**: Area of ellipse described by SD1 and SD2 (``pi * SD1 * SD2``). It is
    proportional to *SD1SD2*.
    - **HRV_CSI**: The Cardiac Sympathetic Index (Toichi, 1997), calculated by dividing the
    longitudinal variability of the Poincaré plot (``4*SD2``) by its transverse variability (``4*SD1``).
    - **HRV_CVI**: The Cardiac Vagal Index (Toichi, 1997), equal to the logarithm of the product of
    longitudinal (``4*SD2``) and transverse variability (``4*SD1``).
    - **HRV_CSI_Modified**: The modified CSI (Jeppesen, 2014) obtained by dividing the square of
    the longitudinal variability by its transverse variability.
- **Indices of Heart Rate Asymmetry (HRA), i.e., asymmetry of the Poincaré plot** (Yan, 2017):
    - **HRV_GI**: Guzik's Index, defined as the distance of points above line of identity (LI)
    to LI divided by the distance of all points in Poincaré plot to LI except those that
    are located on LI.
    - **HRV_SI**: Slope Index, defined as the phase angle of points above LI divided by the
    phase angle of all points in Poincaré plot except those that are located on LI.
    - **HRV_AI**: Area Index, defined as the cumulative area of the sectors corresponding to
    the points that are located above LI divided by the cumulative area of sectors
    corresponding to all points in the Poincaré plot except those that are located on LI.
    - **HRV_PI**: Porta's Index, defined as the number of points below LI divided by the total
    number of points in Poincaré plot except those that are located on LI.
    - **HRV_SD1d** and **HRV_SD1a**: short-term variance of contributions of decelerations
    (prolongations of RR intervals) and accelerations (shortenings of RR intervals),
    respectively (Piskorski,  2011).
    - **HRV_C1d** and **HRV_C1a**: the contributions of heart rate decelerations and accelerations
    to short-term HRV, respectively (Piskorski,  2011).
    - **HRV_SD2d** and **HRV_SD2a**: long-term variance of contributions of decelerations
    (prolongations of RR intervals) and accelerations (shortenings of RR intervals),
    respectively (Piskorski,  2011).
    - **HRV_C2d** and **HRV_C2a**: the contributions of heart rate decelerations and accelerations
    to long-term HRV, respectively (Piskorski,  2011).
    - **HRV_SDNNd** and **HRV_SDNNa**: total variance of contributions of decelerations
    (prolongations of RR intervals) and accelerations (shortenings of RR intervals),
    respectively (Piskorski,  2011).
    - **HRV_Cd** and **HRV_Ca**: the total contributions of heart rate decelerations and
    accelerations to HRV.
- **Indices of Heart Rate Fragmentation** (Costa, 2017):
    - **HRV_PIP**: Percentage of inflection points of the RR intervals series.
    - **HRV_IALS**: Inverse of the average length of the acceleration/deceleration segments.
    - **HRV_PSS**: Percentage of short segments.
    - **HRV_PAS**: IPercentage of NN intervals in alternation segments.
- **Indices of Complexity**:
    - **HRV_ApEn**: The approximate entropy measure of HRV, calculated by `entropy_approximate()`.
    - **HRV_SampEn**: The sample entropy measure of HRV, calculated by `entropy_sample()`.
"""

HB_SIG_TSFRESH_COLS = [
    "hb_sig__abs_energy",
    "hb_sig__absolute_sum_of_changes",
    'hb_sig__agg_autocorrelation__f_agg_"mean"__maxlag_40',
    'hb_sig__agg_autocorrelation__f_agg_"median"__maxlag_40',
    'hb_sig__agg_autocorrelation__f_agg_"var"__maxlag_40',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"var"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"max"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"mean"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"min"',
    'hb_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"var"',
    "hb_sig__approximate_entropy__m_2__r_0.1",
    "hb_sig__approximate_entropy__m_2__r_0.3",
    "hb_sig__approximate_entropy__m_2__r_0.5",
    "hb_sig__approximate_entropy__m_2__r_0.7",
    "hb_sig__approximate_entropy__m_2__r_0.9",
    "hb_sig__ar_coefficient__coeff_0__k_10",
    "hb_sig__ar_coefficient__coeff_10__k_10",
    "hb_sig__ar_coefficient__coeff_1__k_10",
    "hb_sig__ar_coefficient__coeff_2__k_10",
    "hb_sig__ar_coefficient__coeff_3__k_10",
    "hb_sig__ar_coefficient__coeff_4__k_10",
    "hb_sig__ar_coefficient__coeff_5__k_10",
    "hb_sig__ar_coefficient__coeff_6__k_10",
    "hb_sig__ar_coefficient__coeff_7__k_10",
    "hb_sig__ar_coefficient__coeff_8__k_10",
    "hb_sig__ar_coefficient__coeff_9__k_10",
    'hb_sig__augmented_dickey_fuller__attr_"pvalue"__autolag_"AIC"',
    'hb_sig__augmented_dickey_fuller__attr_"teststat"__autolag_"AIC"',
    'hb_sig__augmented_dickey_fuller__attr_"usedlag"__autolag_"AIC"',
    "hb_sig__autocorrelation__lag_0",
    "hb_sig__autocorrelation__lag_1",
    "hb_sig__autocorrelation__lag_2",
    "hb_sig__autocorrelation__lag_3",
    "hb_sig__autocorrelation__lag_4",
    "hb_sig__autocorrelation__lag_5",
    "hb_sig__autocorrelation__lag_6",
    "hb_sig__autocorrelation__lag_7",
    "hb_sig__autocorrelation__lag_8",
    "hb_sig__autocorrelation__lag_9",
    "hb_sig__binned_entropy__max_bins_10",
    "hb_sig__c3__lag_1",
    "hb_sig__c3__lag_2",
    "hb_sig__c3__lag_3",
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.2__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.4__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.4__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.6__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.6__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.6__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.8',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.2__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.4__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.4__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.6__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.6__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.6__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.8',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.2__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.4__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.4__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.6__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.6__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.6__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.8',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.2__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.4__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.4__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.6__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.6__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.6__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.0',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.2',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.4',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.6',
    'hb_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.8',
    "hb_sig__cid_ce__normalize_False",
    "hb_sig__cid_ce__normalize_True",
    "hb_sig__count_above__t_0",
    "hb_sig__count_above_mean",
    "hb_sig__count_below__t_0",
    "hb_sig__count_below_mean",
    "hb_sig__cwt_coefficients__coeff_0__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_0__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_0__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_0__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_10__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_10__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_10__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_10__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_11__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_11__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_11__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_11__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_12__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_12__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_12__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_12__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_13__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_13__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_13__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_13__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_14__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_14__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_14__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_14__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_1__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_1__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_1__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_1__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_2__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_2__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_2__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_2__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_3__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_3__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_3__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_3__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_4__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_4__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_4__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_4__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_5__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_5__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_5__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_5__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_6__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_6__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_6__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_6__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_7__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_7__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_7__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_7__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_8__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_8__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_8__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_8__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_9__w_10__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_9__w_20__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_9__w_2__widths_(2, 5, 10, 20)",
    "hb_sig__cwt_coefficients__coeff_9__w_5__widths_(2, 5, 10, 20)",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_0",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_1",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_2",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_3",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_4",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_5",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_6",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_7",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_8",
    "hb_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_9",
    'hb_sig__fft_aggregated__aggtype_"centroid"',
    'hb_sig__fft_aggregated__aggtype_"kurtosis"',
    'hb_sig__fft_aggregated__aggtype_"skew"',
    'hb_sig__fft_aggregated__aggtype_"variance"',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_0',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_1',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_10',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_11',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_12',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_13',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_14',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_15',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_16',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_17',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_18',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_19',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_2',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_20',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_21',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_22',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_23',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_24',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_25',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_26',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_27',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_28',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_29',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_3',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_30',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_31',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_32',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_33',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_34',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_35',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_36',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_37',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_38',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_39',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_4',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_40',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_41',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_42',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_43',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_44',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_45',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_46',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_47',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_48',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_49',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_5',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_50',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_51',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_52',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_53',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_54',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_55',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_56',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_57',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_58',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_59',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_6',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_60',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_61',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_62',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_63',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_64',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_65',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_66',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_67',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_68',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_69',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_7',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_70',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_71',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_72',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_73',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_74',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_75',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_76',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_77',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_78',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_79',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_8',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_80',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_81',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_82',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_83',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_84',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_85',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_86',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_87',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_88',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_89',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_9',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_90',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_91',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_92',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_93',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_94',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_95',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_96',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_97',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_98',
    'hb_sig__fft_coefficient__attr_"abs"__coeff_99',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_0',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_1',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_10',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_11',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_12',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_13',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_14',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_15',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_16',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_17',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_18',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_19',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_2',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_20',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_21',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_22',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_23',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_24',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_25',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_26',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_27',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_28',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_29',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_3',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_30',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_31',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_32',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_33',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_34',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_35',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_36',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_37',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_38',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_39',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_4',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_40',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_41',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_42',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_43',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_44',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_45',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_46',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_47',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_48',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_49',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_5',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_50',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_51',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_52',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_53',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_54',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_55',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_56',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_57',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_58',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_59',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_6',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_60',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_61',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_62',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_63',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_64',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_65',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_66',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_67',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_68',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_69',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_7',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_70',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_71',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_72',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_73',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_74',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_75',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_76',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_77',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_78',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_79',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_8',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_80',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_81',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_82',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_83',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_84',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_85',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_86',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_87',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_88',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_89',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_9',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_90',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_91',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_92',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_93',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_94',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_95',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_96',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_97',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_98',
    'hb_sig__fft_coefficient__attr_"angle"__coeff_99',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_0',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_1',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_10',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_11',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_12',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_13',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_14',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_15',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_16',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_17',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_18',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_19',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_2',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_20',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_21',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_22',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_23',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_24',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_25',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_26',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_27',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_28',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_29',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_3',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_30',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_31',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_32',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_33',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_34',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_35',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_36',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_37',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_38',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_39',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_4',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_40',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_41',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_42',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_43',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_44',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_45',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_46',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_47',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_48',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_49',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_5',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_50',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_51',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_52',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_53',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_54',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_55',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_56',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_57',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_58',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_59',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_6',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_60',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_61',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_62',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_63',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_64',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_65',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_66',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_67',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_68',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_69',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_7',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_70',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_71',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_72',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_73',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_74',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_75',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_76',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_77',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_78',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_79',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_8',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_80',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_81',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_82',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_83',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_84',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_85',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_86',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_87',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_88',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_89',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_9',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_90',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_91',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_92',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_93',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_94',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_95',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_96',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_97',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_98',
    'hb_sig__fft_coefficient__attr_"imag"__coeff_99',
    'hb_sig__fft_coefficient__attr_"real"__coeff_0',
    'hb_sig__fft_coefficient__attr_"real"__coeff_1',
    'hb_sig__fft_coefficient__attr_"real"__coeff_10',
    'hb_sig__fft_coefficient__attr_"real"__coeff_11',
    'hb_sig__fft_coefficient__attr_"real"__coeff_12',
    'hb_sig__fft_coefficient__attr_"real"__coeff_13',
    'hb_sig__fft_coefficient__attr_"real"__coeff_14',
    'hb_sig__fft_coefficient__attr_"real"__coeff_15',
    'hb_sig__fft_coefficient__attr_"real"__coeff_16',
    'hb_sig__fft_coefficient__attr_"real"__coeff_17',
    'hb_sig__fft_coefficient__attr_"real"__coeff_18',
    'hb_sig__fft_coefficient__attr_"real"__coeff_19',
    'hb_sig__fft_coefficient__attr_"real"__coeff_2',
    'hb_sig__fft_coefficient__attr_"real"__coeff_20',
    'hb_sig__fft_coefficient__attr_"real"__coeff_21',
    'hb_sig__fft_coefficient__attr_"real"__coeff_22',
    'hb_sig__fft_coefficient__attr_"real"__coeff_23',
    'hb_sig__fft_coefficient__attr_"real"__coeff_24',
    'hb_sig__fft_coefficient__attr_"real"__coeff_25',
    'hb_sig__fft_coefficient__attr_"real"__coeff_26',
    'hb_sig__fft_coefficient__attr_"real"__coeff_27',
    'hb_sig__fft_coefficient__attr_"real"__coeff_28',
    'hb_sig__fft_coefficient__attr_"real"__coeff_29',
    'hb_sig__fft_coefficient__attr_"real"__coeff_3',
    'hb_sig__fft_coefficient__attr_"real"__coeff_30',
    'hb_sig__fft_coefficient__attr_"real"__coeff_31',
    'hb_sig__fft_coefficient__attr_"real"__coeff_32',
    'hb_sig__fft_coefficient__attr_"real"__coeff_33',
    'hb_sig__fft_coefficient__attr_"real"__coeff_34',
    'hb_sig__fft_coefficient__attr_"real"__coeff_35',
    'hb_sig__fft_coefficient__attr_"real"__coeff_36',
    'hb_sig__fft_coefficient__attr_"real"__coeff_37',
    'hb_sig__fft_coefficient__attr_"real"__coeff_38',
    'hb_sig__fft_coefficient__attr_"real"__coeff_39',
    'hb_sig__fft_coefficient__attr_"real"__coeff_4',
    'hb_sig__fft_coefficient__attr_"real"__coeff_40',
    'hb_sig__fft_coefficient__attr_"real"__coeff_41',
    'hb_sig__fft_coefficient__attr_"real"__coeff_42',
    'hb_sig__fft_coefficient__attr_"real"__coeff_43',
    'hb_sig__fft_coefficient__attr_"real"__coeff_44',
    'hb_sig__fft_coefficient__attr_"real"__coeff_45',
    'hb_sig__fft_coefficient__attr_"real"__coeff_46',
    'hb_sig__fft_coefficient__attr_"real"__coeff_47',
    'hb_sig__fft_coefficient__attr_"real"__coeff_48',
    'hb_sig__fft_coefficient__attr_"real"__coeff_49',
    'hb_sig__fft_coefficient__attr_"real"__coeff_5',
    'hb_sig__fft_coefficient__attr_"real"__coeff_50',
    'hb_sig__fft_coefficient__attr_"real"__coeff_51',
    'hb_sig__fft_coefficient__attr_"real"__coeff_52',
    'hb_sig__fft_coefficient__attr_"real"__coeff_53',
    'hb_sig__fft_coefficient__attr_"real"__coeff_54',
    'hb_sig__fft_coefficient__attr_"real"__coeff_55',
    'hb_sig__fft_coefficient__attr_"real"__coeff_56',
    'hb_sig__fft_coefficient__attr_"real"__coeff_57',
    'hb_sig__fft_coefficient__attr_"real"__coeff_58',
    'hb_sig__fft_coefficient__attr_"real"__coeff_59',
    'hb_sig__fft_coefficient__attr_"real"__coeff_6',
    'hb_sig__fft_coefficient__attr_"real"__coeff_60',
    'hb_sig__fft_coefficient__attr_"real"__coeff_61',
    'hb_sig__fft_coefficient__attr_"real"__coeff_62',
    'hb_sig__fft_coefficient__attr_"real"__coeff_63',
    'hb_sig__fft_coefficient__attr_"real"__coeff_64',
    'hb_sig__fft_coefficient__attr_"real"__coeff_65',
    'hb_sig__fft_coefficient__attr_"real"__coeff_66',
    'hb_sig__fft_coefficient__attr_"real"__coeff_67',
    'hb_sig__fft_coefficient__attr_"real"__coeff_68',
    'hb_sig__fft_coefficient__attr_"real"__coeff_69',
    'hb_sig__fft_coefficient__attr_"real"__coeff_7',
    'hb_sig__fft_coefficient__attr_"real"__coeff_70',
    'hb_sig__fft_coefficient__attr_"real"__coeff_71',
    'hb_sig__fft_coefficient__attr_"real"__coeff_72',
    'hb_sig__fft_coefficient__attr_"real"__coeff_73',
    'hb_sig__fft_coefficient__attr_"real"__coeff_74',
    'hb_sig__fft_coefficient__attr_"real"__coeff_75',
    'hb_sig__fft_coefficient__attr_"real"__coeff_76',
    'hb_sig__fft_coefficient__attr_"real"__coeff_77',
    'hb_sig__fft_coefficient__attr_"real"__coeff_78',
    'hb_sig__fft_coefficient__attr_"real"__coeff_79',
    'hb_sig__fft_coefficient__attr_"real"__coeff_8',
    'hb_sig__fft_coefficient__attr_"real"__coeff_80',
    'hb_sig__fft_coefficient__attr_"real"__coeff_81',
    'hb_sig__fft_coefficient__attr_"real"__coeff_82',
    'hb_sig__fft_coefficient__attr_"real"__coeff_83',
    'hb_sig__fft_coefficient__attr_"real"__coeff_84',
    'hb_sig__fft_coefficient__attr_"real"__coeff_85',
    'hb_sig__fft_coefficient__attr_"real"__coeff_86',
    'hb_sig__fft_coefficient__attr_"real"__coeff_87',
    'hb_sig__fft_coefficient__attr_"real"__coeff_88',
    'hb_sig__fft_coefficient__attr_"real"__coeff_89',
    'hb_sig__fft_coefficient__attr_"real"__coeff_9',
    'hb_sig__fft_coefficient__attr_"real"__coeff_90',
    'hb_sig__fft_coefficient__attr_"real"__coeff_91',
    'hb_sig__fft_coefficient__attr_"real"__coeff_92',
    'hb_sig__fft_coefficient__attr_"real"__coeff_93',
    'hb_sig__fft_coefficient__attr_"real"__coeff_94',
    'hb_sig__fft_coefficient__attr_"real"__coeff_95',
    'hb_sig__fft_coefficient__attr_"real"__coeff_96',
    'hb_sig__fft_coefficient__attr_"real"__coeff_97',
    'hb_sig__fft_coefficient__attr_"real"__coeff_98',
    'hb_sig__fft_coefficient__attr_"real"__coeff_99',
    "hb_sig__first_location_of_maximum",
    "hb_sig__first_location_of_minimum",
    "hb_sig__friedrich_coefficients__coeff_0__m_3__r_30",
    "hb_sig__friedrich_coefficients__coeff_1__m_3__r_30",
    "hb_sig__friedrich_coefficients__coeff_2__m_3__r_30",
    "hb_sig__friedrich_coefficients__coeff_3__m_3__r_30",
    "hb_sig__has_duplicate",
    "hb_sig__has_duplicate_max",
    "hb_sig__has_duplicate_min",
    "hb_sig__index_mass_quantile__q_0.1",
    "hb_sig__index_mass_quantile__q_0.2",
    "hb_sig__index_mass_quantile__q_0.3",
    "hb_sig__index_mass_quantile__q_0.4",
    "hb_sig__index_mass_quantile__q_0.6",
    "hb_sig__index_mass_quantile__q_0.7",
    "hb_sig__index_mass_quantile__q_0.8",
    "hb_sig__index_mass_quantile__q_0.9",
    "hb_sig__kurtosis",
    "hb_sig__large_standard_deviation__r_0.05",
    "hb_sig__large_standard_deviation__r_0.1",
    "hb_sig__large_standard_deviation__r_0.15000000000000002",
    "hb_sig__large_standard_deviation__r_0.2",
    "hb_sig__large_standard_deviation__r_0.25",
    "hb_sig__large_standard_deviation__r_0.30000000000000004",
    "hb_sig__large_standard_deviation__r_0.35000000000000003",
    "hb_sig__large_standard_deviation__r_0.4",
    "hb_sig__large_standard_deviation__r_0.45",
    "hb_sig__large_standard_deviation__r_0.5",
    "hb_sig__large_standard_deviation__r_0.55",
    "hb_sig__large_standard_deviation__r_0.6000000000000001",
    "hb_sig__large_standard_deviation__r_0.65",
    "hb_sig__large_standard_deviation__r_0.7000000000000001",
    "hb_sig__large_standard_deviation__r_0.75",
    "hb_sig__large_standard_deviation__r_0.8",
    "hb_sig__large_standard_deviation__r_0.8500000000000001",
    "hb_sig__large_standard_deviation__r_0.9",
    "hb_sig__large_standard_deviation__r_0.9500000000000001",
    "hb_sig__last_location_of_maximum",
    "hb_sig__last_location_of_minimum",
    "hb_sig__length",
    'hb_sig__linear_trend__attr_"intercept"',
    'hb_sig__linear_trend__attr_"pvalue"',
    'hb_sig__linear_trend__attr_"rvalue"',
    'hb_sig__linear_trend__attr_"slope"',
    'hb_sig__linear_trend__attr_"stderr"',
    "hb_sig__longest_strike_above_mean",
    "hb_sig__longest_strike_below_mean",
    "hb_sig__max_langevin_fixed_point__m_3__r_30",
    "hb_sig__maximum",
    "hb_sig__mean",
    "hb_sig__mean_abs_change",
    "hb_sig__mean_change",
    "hb_sig__mean_second_derivative_central",
    "hb_sig__median",
    "hb_sig__minimum",
    "hb_sig__number_crossing_m__m_-1",
    "hb_sig__number_crossing_m__m_0",
    "hb_sig__number_crossing_m__m_1",
    "hb_sig__number_cwt_peaks__n_1",
    "hb_sig__number_cwt_peaks__n_5",
    "hb_sig__number_peaks__n_1",
    "hb_sig__number_peaks__n_10",
    "hb_sig__number_peaks__n_3",
    "hb_sig__number_peaks__n_5",
    "hb_sig__number_peaks__n_50",
    "hb_sig__partial_autocorrelation__lag_0",
    "hb_sig__partial_autocorrelation__lag_1",
    "hb_sig__partial_autocorrelation__lag_2",
    "hb_sig__partial_autocorrelation__lag_3",
    "hb_sig__partial_autocorrelation__lag_4",
    "hb_sig__partial_autocorrelation__lag_5",
    "hb_sig__partial_autocorrelation__lag_6",
    "hb_sig__partial_autocorrelation__lag_7",
    "hb_sig__partial_autocorrelation__lag_8",
    "hb_sig__partial_autocorrelation__lag_9",
    "hb_sig__percentage_of_reoccurring_datapoints_to_all_datapoints",
    "hb_sig__percentage_of_reoccurring_values_to_all_values",
    "hb_sig__quantile__q_0.1",
    "hb_sig__quantile__q_0.2",
    "hb_sig__quantile__q_0.3",
    "hb_sig__quantile__q_0.4",
    "hb_sig__quantile__q_0.6",
    "hb_sig__quantile__q_0.7",
    "hb_sig__quantile__q_0.8",
    "hb_sig__quantile__q_0.9",
    "hb_sig__range_count__max_0__min_1000000000000.0",
    "hb_sig__range_count__max_1000000000000.0__min_0",
    "hb_sig__range_count__max_1__min_-1",
    "hb_sig__ratio_beyond_r_sigma__r_0.5",
    "hb_sig__ratio_beyond_r_sigma__r_1",
    "hb_sig__ratio_beyond_r_sigma__r_1.5",
    "hb_sig__ratio_beyond_r_sigma__r_10",
    "hb_sig__ratio_beyond_r_sigma__r_2",
    "hb_sig__ratio_beyond_r_sigma__r_2.5",
    "hb_sig__ratio_beyond_r_sigma__r_3",
    "hb_sig__ratio_beyond_r_sigma__r_5",
    "hb_sig__ratio_beyond_r_sigma__r_6",
    "hb_sig__ratio_beyond_r_sigma__r_7",
    "hb_sig__ratio_value_number_to_time_series_length",
    "hb_sig__sample_entropy",
    "hb_sig__skewness",
    "hb_sig__spkt_welch_density__coeff_2",
    "hb_sig__spkt_welch_density__coeff_5",
    "hb_sig__spkt_welch_density__coeff_8",
    "hb_sig__standard_deviation",
    "hb_sig__sum_of_reoccurring_data_points",
    "hb_sig__sum_of_reoccurring_values",
    "hb_sig__sum_values",
    "hb_sig__symmetry_looking__r_0.0",
    "hb_sig__symmetry_looking__r_0.05",
    "hb_sig__symmetry_looking__r_0.1",
    "hb_sig__symmetry_looking__r_0.15000000000000002",
    "hb_sig__symmetry_looking__r_0.2",
    "hb_sig__symmetry_looking__r_0.25",
    "hb_sig__symmetry_looking__r_0.30000000000000004",
    "hb_sig__symmetry_looking__r_0.35000000000000003",
    "hb_sig__symmetry_looking__r_0.4",
    "hb_sig__symmetry_looking__r_0.45",
    "hb_sig__symmetry_looking__r_0.5",
    "hb_sig__symmetry_looking__r_0.55",
    "hb_sig__symmetry_looking__r_0.6000000000000001",
    "hb_sig__symmetry_looking__r_0.65",
    "hb_sig__symmetry_looking__r_0.7000000000000001",
    "hb_sig__symmetry_looking__r_0.75",
    "hb_sig__symmetry_looking__r_0.8",
    "hb_sig__symmetry_looking__r_0.8500000000000001",
    "hb_sig__symmetry_looking__r_0.9",
    "hb_sig__symmetry_looking__r_0.9500000000000001",
    "hb_sig__time_reversal_asymmetry_statistic__lag_1",
    "hb_sig__time_reversal_asymmetry_statistic__lag_2",
    "hb_sig__time_reversal_asymmetry_statistic__lag_3",
    "hb_sig__value_count__value_-1",
    "hb_sig__value_count__value_0",
    "hb_sig__value_count__value_1",
    "hb_sig__variance",
    "hb_sig__variance_larger_than_standard_deviation",
    "hb_sig__variation_coefficient",
]

LEAD_SIG_TSFRESH_COLS = [
    "lead_sig__abs_energy",
    "lead_sig__absolute_sum_of_changes",
    'lead_sig__agg_autocorrelation__f_agg_"mean"__maxlag_40',
    'lead_sig__agg_autocorrelation__f_agg_"median"__maxlag_40',
    'lead_sig__agg_autocorrelation__f_agg_"var"__maxlag_40',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_10__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_50__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"intercept"__chunk_len_5__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_10__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_50__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"rvalue"__chunk_len_5__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_10__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_50__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"slope"__chunk_len_5__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_10__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_50__f_agg_"var"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"max"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"mean"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"min"',
    'lead_sig__agg_linear_trend__attr_"stderr"__chunk_len_5__f_agg_"var"',
    "lead_sig__approximate_entropy__m_2__r_0.1",
    "lead_sig__approximate_entropy__m_2__r_0.3",
    "lead_sig__approximate_entropy__m_2__r_0.5",
    "lead_sig__approximate_entropy__m_2__r_0.7",
    "lead_sig__approximate_entropy__m_2__r_0.9",
    "lead_sig__ar_coefficient__coeff_0__k_10",
    "lead_sig__ar_coefficient__coeff_10__k_10",
    "lead_sig__ar_coefficient__coeff_1__k_10",
    "lead_sig__ar_coefficient__coeff_2__k_10",
    "lead_sig__ar_coefficient__coeff_3__k_10",
    "lead_sig__ar_coefficient__coeff_4__k_10",
    "lead_sig__ar_coefficient__coeff_5__k_10",
    "lead_sig__ar_coefficient__coeff_6__k_10",
    "lead_sig__ar_coefficient__coeff_7__k_10",
    "lead_sig__ar_coefficient__coeff_8__k_10",
    "lead_sig__ar_coefficient__coeff_9__k_10",
    'lead_sig__augmented_dickey_fuller__attr_"pvalue"__autolag_"AIC"',
    'lead_sig__augmented_dickey_fuller__attr_"teststat"__autolag_"AIC"',
    'lead_sig__augmented_dickey_fuller__attr_"usedlag"__autolag_"AIC"',
    "lead_sig__autocorrelation__lag_0",
    "lead_sig__autocorrelation__lag_1",
    "lead_sig__autocorrelation__lag_2",
    "lead_sig__autocorrelation__lag_3",
    "lead_sig__autocorrelation__lag_4",
    "lead_sig__autocorrelation__lag_5",
    "lead_sig__autocorrelation__lag_6",
    "lead_sig__autocorrelation__lag_7",
    "lead_sig__autocorrelation__lag_8",
    "lead_sig__autocorrelation__lag_9",
    "lead_sig__binned_entropy__max_bins_10",
    "lead_sig__c3__lag_1",
    "lead_sig__c3__lag_2",
    "lead_sig__c3__lag_3",
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.2__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.4__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.4__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.6__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.6__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.6__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_0.8__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_False__qh_1.0__ql_0.8',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.2__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.4__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.4__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.6__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.6__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.6__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_0.8__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"mean"__isabs_True__qh_1.0__ql_0.8',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.2__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.4__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.4__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.6__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.6__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.6__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_0.8__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_False__qh_1.0__ql_0.8',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.2__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.4__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.4__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.6__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.6__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.6__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_0.8__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.0',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.2',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.4',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.6',
    'lead_sig__change_quantiles__f_agg_"var"__isabs_True__qh_1.0__ql_0.8',
    "lead_sig__cid_ce__normalize_False",
    "lead_sig__cid_ce__normalize_True",
    "lead_sig__count_above__t_0",
    "lead_sig__count_above_mean",
    "lead_sig__count_below__t_0",
    "lead_sig__count_below_mean",
    "lead_sig__cwt_coefficients__coeff_0__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_0__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_0__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_0__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_10__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_10__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_10__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_10__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_11__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_11__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_11__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_11__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_12__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_12__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_12__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_12__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_13__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_13__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_13__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_13__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_14__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_14__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_14__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_14__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_1__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_1__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_1__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_1__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_2__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_2__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_2__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_2__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_3__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_3__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_3__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_3__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_4__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_4__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_4__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_4__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_5__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_5__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_5__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_5__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_6__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_6__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_6__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_6__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_7__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_7__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_7__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_7__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_8__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_8__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_8__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_8__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_9__w_10__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_9__w_20__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_9__w_2__widths_(2, 5, 10, 20)",
    "lead_sig__cwt_coefficients__coeff_9__w_5__widths_(2, 5, 10, 20)",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_0",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_1",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_2",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_3",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_4",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_5",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_6",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_7",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_8",
    "lead_sig__energy_ratio_by_chunks__num_segments_10__segment_focus_9",
    'lead_sig__fft_aggregated__aggtype_"centroid"',
    'lead_sig__fft_aggregated__aggtype_"kurtosis"',
    'lead_sig__fft_aggregated__aggtype_"skew"',
    'lead_sig__fft_aggregated__aggtype_"variance"',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_0',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_1',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_10',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_11',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_12',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_13',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_14',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_15',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_16',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_17',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_18',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_19',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_2',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_20',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_21',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_22',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_23',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_24',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_25',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_26',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_27',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_28',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_29',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_3',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_30',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_31',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_32',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_33',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_34',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_35',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_36',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_37',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_38',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_39',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_4',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_40',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_41',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_42',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_43',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_44',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_45',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_46',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_47',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_48',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_49',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_5',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_50',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_51',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_52',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_53',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_54',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_55',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_56',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_57',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_58',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_59',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_6',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_60',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_61',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_62',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_63',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_64',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_65',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_66',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_67',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_68',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_69',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_7',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_70',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_71',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_72',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_73',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_74',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_75',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_76',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_77',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_78',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_79',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_8',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_80',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_81',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_82',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_83',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_84',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_85',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_86',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_87',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_88',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_89',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_9',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_90',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_91',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_92',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_93',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_94',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_95',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_96',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_97',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_98',
    'lead_sig__fft_coefficient__attr_"abs"__coeff_99',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_0',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_1',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_10',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_11',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_12',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_13',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_14',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_15',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_16',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_17',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_18',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_19',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_2',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_20',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_21',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_22',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_23',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_24',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_25',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_26',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_27',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_28',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_29',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_3',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_30',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_31',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_32',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_33',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_34',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_35',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_36',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_37',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_38',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_39',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_4',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_40',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_41',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_42',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_43',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_44',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_45',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_46',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_47',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_48',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_49',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_5',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_50',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_51',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_52',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_53',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_54',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_55',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_56',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_57',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_58',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_59',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_6',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_60',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_61',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_62',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_63',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_64',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_65',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_66',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_67',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_68',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_69',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_7',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_70',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_71',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_72',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_73',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_74',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_75',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_76',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_77',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_78',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_79',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_8',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_80',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_81',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_82',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_83',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_84',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_85',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_86',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_87',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_88',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_89',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_9',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_90',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_91',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_92',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_93',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_94',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_95',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_96',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_97',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_98',
    'lead_sig__fft_coefficient__attr_"angle"__coeff_99',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_0',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_1',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_10',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_11',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_12',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_13',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_14',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_15',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_16',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_17',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_18',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_19',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_2',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_20',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_21',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_22',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_23',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_24',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_25',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_26',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_27',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_28',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_29',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_3',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_30',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_31',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_32',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_33',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_34',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_35',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_36',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_37',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_38',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_39',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_4',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_40',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_41',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_42',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_43',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_44',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_45',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_46',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_47',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_48',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_49',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_5',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_50',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_51',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_52',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_53',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_54',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_55',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_56',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_57',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_58',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_59',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_6',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_60',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_61',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_62',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_63',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_64',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_65',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_66',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_67',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_68',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_69',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_7',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_70',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_71',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_72',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_73',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_74',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_75',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_76',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_77',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_78',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_79',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_8',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_80',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_81',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_82',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_83',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_84',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_85',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_86',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_87',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_88',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_89',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_9',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_90',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_91',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_92',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_93',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_94',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_95',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_96',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_97',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_98',
    'lead_sig__fft_coefficient__attr_"imag"__coeff_99',
    'lead_sig__fft_coefficient__attr_"real"__coeff_0',
    'lead_sig__fft_coefficient__attr_"real"__coeff_1',
    'lead_sig__fft_coefficient__attr_"real"__coeff_10',
    'lead_sig__fft_coefficient__attr_"real"__coeff_11',
    'lead_sig__fft_coefficient__attr_"real"__coeff_12',
    'lead_sig__fft_coefficient__attr_"real"__coeff_13',
    'lead_sig__fft_coefficient__attr_"real"__coeff_14',
    'lead_sig__fft_coefficient__attr_"real"__coeff_15',
    'lead_sig__fft_coefficient__attr_"real"__coeff_16',
    'lead_sig__fft_coefficient__attr_"real"__coeff_17',
    'lead_sig__fft_coefficient__attr_"real"__coeff_18',
    'lead_sig__fft_coefficient__attr_"real"__coeff_19',
    'lead_sig__fft_coefficient__attr_"real"__coeff_2',
    'lead_sig__fft_coefficient__attr_"real"__coeff_20',
    'lead_sig__fft_coefficient__attr_"real"__coeff_21',
    'lead_sig__fft_coefficient__attr_"real"__coeff_22',
    'lead_sig__fft_coefficient__attr_"real"__coeff_23',
    'lead_sig__fft_coefficient__attr_"real"__coeff_24',
    'lead_sig__fft_coefficient__attr_"real"__coeff_25',
    'lead_sig__fft_coefficient__attr_"real"__coeff_26',
    'lead_sig__fft_coefficient__attr_"real"__coeff_27',
    'lead_sig__fft_coefficient__attr_"real"__coeff_28',
    'lead_sig__fft_coefficient__attr_"real"__coeff_29',
    'lead_sig__fft_coefficient__attr_"real"__coeff_3',
    'lead_sig__fft_coefficient__attr_"real"__coeff_30',
    'lead_sig__fft_coefficient__attr_"real"__coeff_31',
    'lead_sig__fft_coefficient__attr_"real"__coeff_32',
    'lead_sig__fft_coefficient__attr_"real"__coeff_33',
    'lead_sig__fft_coefficient__attr_"real"__coeff_34',
    'lead_sig__fft_coefficient__attr_"real"__coeff_35',
    'lead_sig__fft_coefficient__attr_"real"__coeff_36',
    'lead_sig__fft_coefficient__attr_"real"__coeff_37',
    'lead_sig__fft_coefficient__attr_"real"__coeff_38',
    'lead_sig__fft_coefficient__attr_"real"__coeff_39',
    'lead_sig__fft_coefficient__attr_"real"__coeff_4',
    'lead_sig__fft_coefficient__attr_"real"__coeff_40',
    'lead_sig__fft_coefficient__attr_"real"__coeff_41',
    'lead_sig__fft_coefficient__attr_"real"__coeff_42',
    'lead_sig__fft_coefficient__attr_"real"__coeff_43',
    'lead_sig__fft_coefficient__attr_"real"__coeff_44',
    'lead_sig__fft_coefficient__attr_"real"__coeff_45',
    'lead_sig__fft_coefficient__attr_"real"__coeff_46',
    'lead_sig__fft_coefficient__attr_"real"__coeff_47',
    'lead_sig__fft_coefficient__attr_"real"__coeff_48',
    'lead_sig__fft_coefficient__attr_"real"__coeff_49',
    'lead_sig__fft_coefficient__attr_"real"__coeff_5',
    'lead_sig__fft_coefficient__attr_"real"__coeff_50',
    'lead_sig__fft_coefficient__attr_"real"__coeff_51',
    'lead_sig__fft_coefficient__attr_"real"__coeff_52',
    'lead_sig__fft_coefficient__attr_"real"__coeff_53',
    'lead_sig__fft_coefficient__attr_"real"__coeff_54',
    'lead_sig__fft_coefficient__attr_"real"__coeff_55',
    'lead_sig__fft_coefficient__attr_"real"__coeff_56',
    'lead_sig__fft_coefficient__attr_"real"__coeff_57',
    'lead_sig__fft_coefficient__attr_"real"__coeff_58',
    'lead_sig__fft_coefficient__attr_"real"__coeff_59',
    'lead_sig__fft_coefficient__attr_"real"__coeff_6',
    'lead_sig__fft_coefficient__attr_"real"__coeff_60',
    'lead_sig__fft_coefficient__attr_"real"__coeff_61',
    'lead_sig__fft_coefficient__attr_"real"__coeff_62',
    'lead_sig__fft_coefficient__attr_"real"__coeff_63',
    'lead_sig__fft_coefficient__attr_"real"__coeff_64',
    'lead_sig__fft_coefficient__attr_"real"__coeff_65',
    'lead_sig__fft_coefficient__attr_"real"__coeff_66',
    'lead_sig__fft_coefficient__attr_"real"__coeff_67',
    'lead_sig__fft_coefficient__attr_"real"__coeff_68',
    'lead_sig__fft_coefficient__attr_"real"__coeff_69',
    'lead_sig__fft_coefficient__attr_"real"__coeff_7',
    'lead_sig__fft_coefficient__attr_"real"__coeff_70',
    'lead_sig__fft_coefficient__attr_"real"__coeff_71',
    'lead_sig__fft_coefficient__attr_"real"__coeff_72',
    'lead_sig__fft_coefficient__attr_"real"__coeff_73',
    'lead_sig__fft_coefficient__attr_"real"__coeff_74',
    'lead_sig__fft_coefficient__attr_"real"__coeff_75',
    'lead_sig__fft_coefficient__attr_"real"__coeff_76',
    'lead_sig__fft_coefficient__attr_"real"__coeff_77',
    'lead_sig__fft_coefficient__attr_"real"__coeff_78',
    'lead_sig__fft_coefficient__attr_"real"__coeff_79',
    'lead_sig__fft_coefficient__attr_"real"__coeff_8',
    'lead_sig__fft_coefficient__attr_"real"__coeff_80',
    'lead_sig__fft_coefficient__attr_"real"__coeff_81',
    'lead_sig__fft_coefficient__attr_"real"__coeff_82',
    'lead_sig__fft_coefficient__attr_"real"__coeff_83',
    'lead_sig__fft_coefficient__attr_"real"__coeff_84',
    'lead_sig__fft_coefficient__attr_"real"__coeff_85',
    'lead_sig__fft_coefficient__attr_"real"__coeff_86',
    'lead_sig__fft_coefficient__attr_"real"__coeff_87',
    'lead_sig__fft_coefficient__attr_"real"__coeff_88',
    'lead_sig__fft_coefficient__attr_"real"__coeff_89',
    'lead_sig__fft_coefficient__attr_"real"__coeff_9',
    'lead_sig__fft_coefficient__attr_"real"__coeff_90',
    'lead_sig__fft_coefficient__attr_"real"__coeff_91',
    'lead_sig__fft_coefficient__attr_"real"__coeff_92',
    'lead_sig__fft_coefficient__attr_"real"__coeff_93',
    'lead_sig__fft_coefficient__attr_"real"__coeff_94',
    'lead_sig__fft_coefficient__attr_"real"__coeff_95',
    'lead_sig__fft_coefficient__attr_"real"__coeff_96',
    'lead_sig__fft_coefficient__attr_"real"__coeff_97',
    'lead_sig__fft_coefficient__attr_"real"__coeff_98',
    'lead_sig__fft_coefficient__attr_"real"__coeff_99',
    "lead_sig__first_location_of_maximum",
    "lead_sig__first_location_of_minimum",
    "lead_sig__friedrich_coefficients__coeff_0__m_3__r_30",
    "lead_sig__friedrich_coefficients__coeff_1__m_3__r_30",
    "lead_sig__friedrich_coefficients__coeff_2__m_3__r_30",
    "lead_sig__friedrich_coefficients__coeff_3__m_3__r_30",
    "lead_sig__has_duplicate",
    "lead_sig__has_duplicate_max",
    "lead_sig__has_duplicate_min",
    "lead_sig__index_mass_quantile__q_0.1",
    "lead_sig__index_mass_quantile__q_0.2",
    "lead_sig__index_mass_quantile__q_0.3",
    "lead_sig__index_mass_quantile__q_0.4",
    "lead_sig__index_mass_quantile__q_0.6",
    "lead_sig__index_mass_quantile__q_0.7",
    "lead_sig__index_mass_quantile__q_0.8",
    "lead_sig__index_mass_quantile__q_0.9",
    "lead_sig__kurtosis",
    "lead_sig__large_standard_deviation__r_0.05",
    "lead_sig__large_standard_deviation__r_0.1",
    "lead_sig__large_standard_deviation__r_0.15000000000000002",
    "lead_sig__large_standard_deviation__r_0.2",
    "lead_sig__large_standard_deviation__r_0.25",
    "lead_sig__large_standard_deviation__r_0.30000000000000004",
    "lead_sig__large_standard_deviation__r_0.35000000000000003",
    "lead_sig__large_standard_deviation__r_0.4",
    "lead_sig__large_standard_deviation__r_0.45",
    "lead_sig__large_standard_deviation__r_0.5",
    "lead_sig__large_standard_deviation__r_0.55",
    "lead_sig__large_standard_deviation__r_0.6000000000000001",
    "lead_sig__large_standard_deviation__r_0.65",
    "lead_sig__large_standard_deviation__r_0.7000000000000001",
    "lead_sig__large_standard_deviation__r_0.75",
    "lead_sig__large_standard_deviation__r_0.8",
    "lead_sig__large_standard_deviation__r_0.8500000000000001",
    "lead_sig__large_standard_deviation__r_0.9",
    "lead_sig__large_standard_deviation__r_0.9500000000000001",
    "lead_sig__last_location_of_maximum",
    "lead_sig__last_location_of_minimum",
    "lead_sig__length",
    'lead_sig__linear_trend__attr_"intercept"',
    'lead_sig__linear_trend__attr_"pvalue"',
    'lead_sig__linear_trend__attr_"rvalue"',
    'lead_sig__linear_trend__attr_"slope"',
    'lead_sig__linear_trend__attr_"stderr"',
    "lead_sig__longest_strike_above_mean",
    "lead_sig__longest_strike_below_mean",
    "lead_sig__max_langevin_fixed_point__m_3__r_30",
    "lead_sig__maximum",
    "lead_sig__mean",
    "lead_sig__mean_abs_change",
    "lead_sig__mean_change",
    "lead_sig__mean_second_derivative_central",
    "lead_sig__median",
    "lead_sig__minimum",
    "lead_sig__number_crossing_m__m_-1",
    "lead_sig__number_crossing_m__m_0",
    "lead_sig__number_crossing_m__m_1",
    "lead_sig__number_cwt_peaks__n_1",
    "lead_sig__number_cwt_peaks__n_5",
    "lead_sig__number_peaks__n_1",
    "lead_sig__number_peaks__n_10",
    "lead_sig__number_peaks__n_3",
    "lead_sig__number_peaks__n_5",
    "lead_sig__number_peaks__n_50",
    "lead_sig__partial_autocorrelation__lag_0",
    "lead_sig__partial_autocorrelation__lag_1",
    "lead_sig__partial_autocorrelation__lag_2",
    "lead_sig__partial_autocorrelation__lag_3",
    "lead_sig__partial_autocorrelation__lag_4",
    "lead_sig__partial_autocorrelation__lag_5",
    "lead_sig__partial_autocorrelation__lag_6",
    "lead_sig__partial_autocorrelation__lag_7",
    "lead_sig__partial_autocorrelation__lag_8",
    "lead_sig__partial_autocorrelation__lag_9",
    "lead_sig__percentage_of_reoccurring_datapoints_to_all_datapoints",
    "lead_sig__percentage_of_reoccurring_values_to_all_values",
    "lead_sig__quantile__q_0.1",
    "lead_sig__quantile__q_0.2",
    "lead_sig__quantile__q_0.3",
    "lead_sig__quantile__q_0.4",
    "lead_sig__quantile__q_0.6",
    "lead_sig__quantile__q_0.7",
    "lead_sig__quantile__q_0.8",
    "lead_sig__quantile__q_0.9",
    "lead_sig__range_count__max_0__min_1000000000000.0",
    "lead_sig__range_count__max_1000000000000.0__min_0",
    "lead_sig__range_count__max_1__min_-1",
    "lead_sig__ratio_beyond_r_sigma__r_0.5",
    "lead_sig__ratio_beyond_r_sigma__r_1",
    "lead_sig__ratio_beyond_r_sigma__r_1.5",
    "lead_sig__ratio_beyond_r_sigma__r_10",
    "lead_sig__ratio_beyond_r_sigma__r_2",
    "lead_sig__ratio_beyond_r_sigma__r_2.5",
    "lead_sig__ratio_beyond_r_sigma__r_3",
    "lead_sig__ratio_beyond_r_sigma__r_5",
    "lead_sig__ratio_beyond_r_sigma__r_6",
    "lead_sig__ratio_beyond_r_sigma__r_7",
    "lead_sig__ratio_value_number_to_time_series_length",
    "lead_sig__sample_entropy",
    "lead_sig__skewness",
    "lead_sig__spkt_welch_density__coeff_2",
    "lead_sig__spkt_welch_density__coeff_5",
    "lead_sig__spkt_welch_density__coeff_8",
    "lead_sig__standard_deviation",
    "lead_sig__sum_of_reoccurring_data_points",
    "lead_sig__sum_of_reoccurring_values",
    "lead_sig__sum_values",
    "lead_sig__symmetry_looking__r_0.0",
    "lead_sig__symmetry_looking__r_0.05",
    "lead_sig__symmetry_looking__r_0.1",
    "lead_sig__symmetry_looking__r_0.15000000000000002",
    "lead_sig__symmetry_looking__r_0.2",
    "lead_sig__symmetry_looking__r_0.25",
    "lead_sig__symmetry_looking__r_0.30000000000000004",
    "lead_sig__symmetry_looking__r_0.35000000000000003",
    "lead_sig__symmetry_looking__r_0.4",
    "lead_sig__symmetry_looking__r_0.45",
    "lead_sig__symmetry_looking__r_0.5",
    "lead_sig__symmetry_looking__r_0.55",
    "lead_sig__symmetry_looking__r_0.6000000000000001",
    "lead_sig__symmetry_looking__r_0.65",
    "lead_sig__symmetry_looking__r_0.7000000000000001",
    "lead_sig__symmetry_looking__r_0.75",
    "lead_sig__symmetry_looking__r_0.8",
    "lead_sig__symmetry_looking__r_0.8500000000000001",
    "lead_sig__symmetry_looking__r_0.9",
    "lead_sig__symmetry_looking__r_0.9500000000000001",
    "lead_sig__time_reversal_asymmetry_statistic__lag_1",
    "lead_sig__time_reversal_asymmetry_statistic__lag_2",
    "lead_sig__time_reversal_asymmetry_statistic__lag_3",
    "lead_sig__value_count__value_-1",
    "lead_sig__value_count__value_0",
    "lead_sig__value_count__value_1",
    "lead_sig__variance",
    "lead_sig__variance_larger_than_standard_deviation",
    "lead_sig__variation_coefficient",
]


def hea_fp_to_np_array(hea_fp):
    """Read a .hea file, convert it into a structured numpy array containing all
    ECG comment metadata and signal features
    """
    record_name = hea_fp.split(".hea")[0]
    r = wfdb.rdrecord(record_name)
    return wfdb_record_to_np_array(r, record_name=record_name)


def data_header_to_np_array(data, header_data):
    """Given the raw signal matrix and header, convert it into a numpy array containing
    all ECG signal features"""
    r = convert_to_wfdb_record(data, header_data)
    return wfdb_record_to_np_array(r, record_name=r.record_name)


def wfdb_record_to_np_array(r, record_name=None):
    if record_name is None:
        record_name = r.record_name
    signal = r.p_signal
    seq_len, num_leads = signal.shape

    # Comment derived features
    dx = []  # target label
    age = float("nan")
    sex = float("nan")

    for comment in r.comments:
        dx_grp = re.search(r"Dx: (?P<dx>.*)$", comment)
        if dx_grp:
            raw_dx = dx_grp.group("dx").split(",")
            for dxi in raw_dx:
                snomed_code = int(dxi)
                dx.append(snomed_code)
            continue

        age_grp = re.search(r"Age: (?P<age>.*)$", comment)
        if age_grp:
            age = float(age_grp.group("age"))
            if not np.isfinite(age):
                age = float("nan")
            continue

        sx_grp = re.search(r"Sex: (?P<sx>.*)$", comment)
        if sx_grp:
            if sx_grp.group("sx").upper().startswith("F"):
                sex = 1.0
            elif sx_grp.group("sx").upper().startswith("M"):
                sex = 0.0
            continue

    # Base structure of numpy array
    data = [record_name, seq_len, r.fs, age, sex, tuple(dx)]
    dtype = [
        ("record_name", np.unicode_, 50),
        ("seq_len", "f8"),
        ("sampling_rate", "f8"),
        ("age", "f8"),
        ("sex", "f8"),
        ("dx", np.object),
    ]

    # Signal derived features (non-parallel)
    # for lead_idx in range(num_leads):
    #     lead_sig = r.p_signal[:, lead_idx]
    #     lead_data, lead_dtype = get_structured_lead_features(
    #         lead_sig, sampling_rate=r.fs, lead_name=r.sig_name[lead_idx]
    #     )
    #     data += lead_data
    #     dtype += lead_dtype

    # Parallel signal derived features
    output = joblib.Parallel(verbose=0, n_jobs=12)(
        joblib.delayed(get_structured_lead_features)(
            r.p_signal[:, lead_idx], sampling_rate=r.fs, lead_name=r.sig_name[lead_idx]
        )
        for lead_idx in range(num_leads)
    )

    for (lead_data, lead_dtype) in output:
        data += lead_data
        dtype += lead_dtype

    return np.array([tuple(data),], dtype=np.dtype(dtype))


def structured_np_array_to_features(np_array):
    """Convert the structured numpy array into an unstructured numpy array of features.
    """
    to_features = [
        n for n in np_array.dtype.names if n not in ("dx", "record_name", "seq_len")
    ]
    return np.array(np_array[to_features].tolist())


def get_structured_lead_features(lead_signal, sampling_rate=500, lead_name=""):
    """From an ECG single lead, return feature values and corresponding dtype
    """
    data = []
    dtype = []

    signals = None
    rpeaks = None

    # HEART RATE VARIABILITY FEATURES
    try:
        ir_data, ir_dtype, signals, rpeaks = _extract_neurokit2_interval_from_signal(
            lead_signal, sampling_rate, lead_name
        )

        # cast into numpy array, parse back out values and dtypes
        data += list(ir_data.tolist()[0])
        dtype += ir_dtype

    except Exception:
        # exc_type, exc_value, exc_traceback = sys.exc_info()
        # print("*** print_tb:")
        # traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
        for k in IR_COLS:
            key = f"{lead_name}_{k}"
            if key not in [d[0] for d in dtype]:
                data.append(float("nan"))
                dtype.append((key, "f8"))

    # HEART BEAT TEMPLATE (PQRST) FEATURES
    try:
        hb_data, hb_dtype = _extract_tsfresh_from_heartbeat(
            signals, rpeaks, sampling_rate, lead_name
        )

        # cast into numpy array, parse back out values and dtypes
        data += list(hb_data.tolist()[0])
        dtype += hb_dtype
    except Exception:
        for k in HB_SIG_TSFRESH_COLS:
            key = f"{lead_name}_{k}"
            if key not in [d[0] for d in dtype]:
                data.append(float("nan"))
                dtype.append((key, "f8"))

    # LONG SIGNAL (~10sec) FEATURES
    try:
        if signals is None:
            ecg_cleaned = nk.ecg_clean(
                lead_signal, sampling_rate=sampling_rate, method="neurokit"
            )

            signals = pd.DataFrame({"ECG_Raw": lead_signal, "ECG_Clean": ecg_cleaned})

        sig_data, sig_dtype = _extract_tsfresh_from_full_signal(
            signals, sampling_rate, lead_name
        )

        data += list(sig_data.tolist()[0])
        dtype += sig_dtype

    except Exception:
        for k in LEAD_SIG_TSFRESH_COLS:
            key = f"{lead_name}_{k}"
            if key not in [d[0] for d in dtype]:
                data.append(float("nan"))
                dtype.append((key, "f8"))

    return data, dtype


def _extract_neurokit2_interval_from_signal(lead_signal, sampling_rate, lead_name):
    ecg_cleaned = nk.ecg_clean(
        lead_signal, sampling_rate=sampling_rate, method="neurokit"
    )

    signals = pd.DataFrame({"ECG_Raw": lead_signal, "ECG_Clean": ecg_cleaned})

    # R-peaks
    instant_peaks, rpeaks, = nk.ecg_peaks(
        ecg_cleaned=ecg_cleaned,
        sampling_rate=sampling_rate,
        method="neurokit",
        correct_artifacts=True,
    )

    rate = nk.signal_rate(
        rpeaks, sampling_rate=sampling_rate, desired_length=len(ecg_cleaned)
    )

    quality = nk.ecg_quality(
        ecg_cleaned, rpeaks=rpeaks["ECG_R_Peaks"], sampling_rate=sampling_rate
    )

    signals = pd.concat(
        [signals, pd.DataFrame({"ECG_Rate": rate, "ECG_Quality": quality,})], axis=1
    )

    # Additional info of the ecg signal
    delineate_signal, delineate_info = nk.ecg_delineate(
        ecg_cleaned=ecg_cleaned, rpeaks=rpeaks, sampling_rate=sampling_rate
    )

    cardiac_phase = nk.ecg_phase(
        ecg_cleaned=ecg_cleaned, rpeaks=rpeaks, delineate_info=delineate_info
    )

    signals = pd.concat(
        [signals, instant_peaks, delineate_signal, cardiac_phase], axis=1
    )

    ir_df = nk.ecg_intervalrelated(signals, sampling_rate=sampling_rate)
    assert all(
        ir_df.columns == IR_COLS
    ), f"interval related feature column mismatch: {lead_name}"

    ir_data = ir_df.to_numpy()
    # ir_elem_dtype = ir_data.dtype
    ir_dtype = []
    for k in ir_df.columns:
        ir_dtype.append((f"{lead_name}_{k}", "f8"))

    return ir_data, ir_dtype, signals, rpeaks


def _extract_tsfresh_from_full_signal(signals, sampling_rate, lead_name):
    lead_signal = signals["ECG_Clean"].to_numpy()

    # convert to 200Hz
    mod_fs = 200
    len_mod_fs = int(len(lead_signal) / sampling_rate * mod_fs)
    lead_signal_mod_fs = sp.signal.resample(lead_signal, len_mod_fs)

    # HARD LIMIT TO 10 SECONDS
    lead_signal_mod_fs = lead_signal_mod_fs[:2000]

    sig_num_samples = len(lead_signal_mod_fs)
    sig_duration = sig_num_samples / mod_fs
    sig_times = np.linspace(0, sig_duration, sig_num_samples).tolist()

    sig_input_df = pd.DataFrame(
        {
            "lead": [lead_name,] * sig_num_samples,
            "time": sig_times,
            "lead_sig": lead_signal_mod_fs.tolist(),
        }
    )

    sig_df = extract_features(
        sig_input_df,
        column_id="lead",
        column_sort="time",
        column_value="lead_sig",
        show_warnings=False,
        disable_progressbar=True,
        n_jobs=0,
    )

    assert all(
        sig_df.columns == LEAD_SIG_TSFRESH_COLS
    ), f"tsfresh feature column mismatch: {lead_name}"

    sig_data = sig_df.to_numpy()
    sig_dtype = []
    for k in sig_df.columns:
        sig_dtype.append((f"{lead_name}_{k}", "f8"))

    return sig_data, sig_dtype


def _extract_tsfresh_from_heartbeat(signals, rpeaks, sampling_rate, lead_name):
    # Determine heart rate windows, get the best heart rate
    heartbeats = nk.ecg_segment(
        signals.rename(columns={"ECG_Clean": "Signal"}).drop(columns=["ECG_Raw"]),
        rpeaks=rpeaks["ECG_R_Peaks"],
        show=False,
    )

    # get the template with maximum quality and no NaN values in signal
    best_idx = None
    best_quality = -1
    for k, v in heartbeats.items():
        if not all(np.isfinite(v["Signal"])):
            continue
        hb_quality_stats = sp.stats.describe(v["ECG_Quality"])
        if hb_quality_stats.mean > best_quality:
            best_idx = k
            best_quality = hb_quality_stats.mean

    best_heartbeat = heartbeats[best_idx]["Signal"]
    hb_num_samples = len(best_heartbeat)
    hb_duration = hb_num_samples / sampling_rate
    hb_times = np.linspace(0, hb_duration, hb_num_samples).tolist()

    hb_input_df = pd.DataFrame(
        {
            "lead": [lead_name,] * hb_num_samples,
            "time": hb_times,
            "hb_sig": best_heartbeat.tolist(),
        }
    )

    hb_df = extract_features(
        hb_input_df,
        column_id="lead",
        column_sort="time",
        column_value="hb_sig",
        show_warnings=False,
        disable_progressbar=True,
        n_jobs=0,
    )

    assert all(
        hb_df.columns == HB_SIG_TSFRESH_COLS
    ), f"tsfresh feature column mismatch: {lead_name}"

    hb_data = hb_df.to_numpy()
    hb_dtype = []
    for k in hb_df.columns:
        hb_dtype.append((f"{lead_name}_{k}", "f8"))

    return hb_data, hb_dtype
