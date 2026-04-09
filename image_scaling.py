#!/usr/bin/env python3

""" IMAGE_SCALING - Routines for image scaling for visualisation
    creation : marin ferrais - APR 2022
"""

#
# --- IMPORTS -----------------------------------------------------------------
#


#
# --- FUNCTIONS ---------------------------------------------------------------
#

def z_scale(data, c=0.05, verbose=False, return_limits=False):
    """
    Z scaling of astronomical image

    Parameters
    ----------
    data : array, required
        Image to be scaled
    c : float, optional
        Contrast value
    verbose : bool, optional
        Print interval values
    """
    from astropy.visualization import ZScaleInterval
    interval = ZScaleInterval(contrast=c)
    limits = interval.get_limits(data)
    if verbose:
        print(limits)
    if return_limits:
        return interval(data.copy()), limits
    else:
        return interval(data.copy())

def minmax_scale(data, verbose=False):
    """
    MinMax scaling of astronomical data

    Parameters
    ----------
    data : array, required
        Image to be scaled
    verbose : bool, optional
        Print interval values
    """
    from astropy.visualization import MinMaxInterval
    interval = MinMaxInterval()
    if verbose:
        print(interval.get_limits(data))
    return interval(data.copy())


def manual_scale(data, vmin=None, vmax=None, verbose=False):
    """
    Manual scaling of astronomical image

    Parameters
    ----------
    data : array, required
        Image to be scaled
    vmin : float, optional
        vmin value to be used in the sacaling
    vmax : float, optional
        vmax value to be used in the sacaling
    verbose : bool, optional
        Print interval values
    """
    from astropy.visualization import ManualInterval
    if not vmax:
        vmax = data.max()
    if not vmin:
        vmin = data[data > 0.05*data.mean()].min()
    interval = ManualInterval(vmin=vmin, vmax=vmax)
    if verbose:
        print(interval.get_limits(data))
    return interval(data.copy())

def percentile_scale(data, percentile=99.5, verbose=False):
    """
    Percentile scaling of astronomical data

    Parameters
    ----------
    data : array, required
        Image to be scaled
    verbose : bool, optional
        Print interval values
    """
    from astropy.visualization import PercentileInterval
    interval = PercentileInterval(percentile=percentile)
    if verbose:
        print(interval.get_limits(data))
    return interval(data.copy())
