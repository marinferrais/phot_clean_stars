#!/usr/bin/env python3

"""  -  PP version

    creation : JUL 2025
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# Numerical computing
import numpy as np

# FITS manipulation + sigma clipping + image visualization
from astropy.io import fits
#from image_scaling import z_scale


# Plotting
import matplotlib.pyplot as plt

# Path manipulation
from pathlib import Path

import sys
sys.path.insert(0, "/home/ferrais/Softwares/photometrypipeline")
import pp_combine
import _pp_conf

# Simple fits image inverter to subtract image
import fits_invert

#
# --- FUNCTIONS ---------------------------------------------------------------
#


def rolling_selection(filenames, i, k=6, p=0, verbose=False):
    """
    
    """
    n = len(filenames)
    k = min(k, n)
    half_k = k // 2

    if i < p:
        if verbose:
            print('c1', i, p, half_k)
        window = filenames[i+1+p:k+i+1+p]
    elif i < half_k+p:
        if verbose:
            print('c2', i, p, half_k)
        window = filenames[:max(0, i-p)] + filenames[i+1+p:k+1+(2*p)]
    elif i > n-p-1:
        if verbose:
            print('c5', i, p, half_k, i-p-k, i-p)
        window = filenames[max(0, i-p-k):i-p]
    elif i > n-half_k-1-p:
        if verbose:
            print('c4', i, p, half_k, n-p)
        window = filenames[max(0, n-k-1-(2*p)):i-p] + filenames[min(n, i+1+p):]     
    else:
        if verbose:
            print('c3', i, p, half_k)
        window = filenames[i-half_k-p:i-p] + filenames[i+1+p:i + half_k+(k%2)+1+p]
    
    if verbose:
        for fname in window:
            print(filenames.index(fname), fname)
        print('')
    
    if len(window) == 0:
        raise ValueError(f"Empty window for frame {filenames[i]} - i={i} - k={k} - p={p}")

    #if (len(window) != k and n > k): # TODO : fix this check for cases with n<=k and p>0 
    #    raise ValueError(f"Window length = {len(window)} is different than k = {k} for i = {i}")

    return window

def pp_check(filenames):
    # read telescope and filter information from fits headers
    # check that they are the same for all images
    instruments = []
    for filename in filenames:
        hdulist = fits.open(filename, ignore_missing_end=True, verify='silentfix')
        header = hdulist[0].header
        for key in _pp_conf.instrument_keys:
            if key in header:
                instruments.append(header[key])

    if len(instruments) == 0:
        raise KeyError('cannot identify telescope/instrument; please update'
                          '_pp_conf.instrument_keys accordingly')

    # assign telescope parameters (telescopes.py)
    telescope = _pp_conf.instrument_identifiers[instruments[0]]
    obsparam = _pp_conf.telescope_parameters[telescope]

    return telescope, obsparam


def pp_median(filenames, windows, keep_medians=False):
    """
    
    """

    wrk_dir = Path(filenames[0]).parent
    med_dir = Path(wrk_dir/'medians')
    res_dir =  Path(wrk_dir/'residuals')
    med_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    telescope, obsparam = pp_check(filenames)

    ppcombine_comoving = False
    targetname = ''
    manual_rates = None
    keep_files = False
    backsub = False

    # compute median
    combinemethod = 'median'
    for i, window in enumerate(windows):
        pp_combine.combine(window, obsparam,
                           ppcombine_comoving, targetname, manual_rates,
                           combinemethod, keep_files, backsub,
                           display=True, diagnostics=True)
        outfile = f'{Path(filenames[i]).stem}_median.fits'
        print(f'> Moving median frame to : {outfile}')
        Path('skycoadd.fits').rename(med_dir/outfile)

    # invert medians
    fits_invert.invert([med_dir/f"{Path(fname).stem}_median.fits" for fname in filenames])
    
    # compute median subtraction
    combinemethod = 'sum'
    for fname in filenames:
        fname = Path(fname)
        median = med_dir/'inverted'/f'{fname.stem}_median_inverted.fits'
        pp_combine.combine([str(fname), str(median)], obsparam,
                           ppcombine_comoving, targetname, manual_rates,
                           combinemethod, keep_files, backsub,
                           display=True, diagnostics=True)
        outfile = res_dir/fname.name
        print(f'> Moving median subtracted frame to : {outfile}')
        Path('skycoadd.fits').rename(outfile)
    
    # Clean up
    if not keep_medians:
        print(f'> Removing directory {med_dir}')
        rmdir(med_dir)
    Path("coadd.weight.fits").unlink()


# Utils functions

def open_fits(fname):
    hdu = fits.open(str(fname))
    header = hdu[0].header
    data = hdu[0].data
    hdu.close()
    return data, header

def rmdir(directory):
    directory = Path(directory)
    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()

def debug_median(images, medians, residuals, index):
    """
    Show original, median, and residual images for a given index.
    """
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    vmin = np.percentile(images[index], 5)
    vmax = np.percentile(images[index], 95)

    axs[0].imshow(images[index], cmap='gray', vmin=vmin, vmax=vmax)
    axs[0].set_title(f'Original [{index}]')
    
    axs[1].imshow(medians[index], cmap='gray', vmin=vmin, vmax=vmax)
    axs[1].set_title('Weighted Median')
    
    axs[2].imshow(residuals[index], cmap='seismic', vmin=-vmax, vmax=vmax)
    axs[2].set_title('Residual (Original - Median)')

    for ax in axs:
        ax.axis('off')
    plt.tight_layout()
    plt.show()

def plot_residual_histogram(residual):
    plt.figure()
    plt.hist(residual.ravel(), bins=100, color='gray')
    plt.title('Histogram of Residual Values')
    plt.xlabel('Residual')
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.show()




#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('filenames', help='list of FITS file names', nargs='+')
    parser.add_argument('-d','--display',
                        help='Display results',
                        action='store_true')
    parser.add_argument('-s','--save',
                        help='Save results to FITS files',
                        action='store_true')
    parser.add_argument('-k',
                        help='Window length for the rolling median',
                        default=5, type=int)
    parser.add_argument('-p',
                        help='Padding around current image for median construction',
                        default=0, type=int)
    parser.add_argument('-km','--keep_medians',
                        help='Do not delete medians file',
                        action='store_true')
    parser.add_argument('-v','--verbose',
                        help='Verbose mode: rolling selectiong details', 
                        action='store_true')

    args = parser.parse_args()

    filenames = sorted(args.filenames)
    display = args.display
    save = args.save
    k = args.k
    p = args.p
    keep_medians = args.keep_medians
    verbose = args.verbose

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #

    windows = []
    for i in range(len(filenames)):
        windows.append(rolling_selection(filenames, i=i, k=k, p=p, verbose=verbose))
    pp_median(filenames, windows, keep_medians=keep_medians)