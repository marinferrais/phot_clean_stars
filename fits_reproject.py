#!/usr/bin/env python3

""" FITS_REPROJECT - Reproject and resample fits2 image on fits1

    creation : JUL 2025
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# Numerical computing
import numpy as np

# Filesytem paths
from pathlib import Path

# FITS manipulation
from astropy.io import fits
from astropy.wcs import WCS
import warnings
from astropy.utils.exceptions import AstropyWarning

# Plotting
import matplotlib.pyplot as plt

# Image reprojection based on WCS
from reproject import reproject_interp

# Progress bar
from tqdm import tqdm

# Strings pattern
import re

from image_scaling import z_scale

#
# --- FUNCTIONS ---------------------------------------------------------------
#

def fix_pp_header(header):
    """
    """
    # Define all known prefixes to check
    wcs_prefixes = ('CRPIX', 'CRVAL', 'CDELT', 'CD', 'PC', 'PV', 'QV', 'CROTA', 'LATPOLE', 'LONPOLE')
    
    # Sanitize values in-place
    for key in list(header.keys()):
        if key.startswith(wcs_prefixes):
            val = header[key]
            if isinstance(val, str):
                try:
                    header[key] = float(val)
                except ValueError:
                    print(f"Skipping malformed WCS value: {key} = {val}")

    # filter out unsupported PVn_m keys
    for key in list(header.keys()):
        if key.startswith('PV'):
            del header[key]

    return header

def reproject(fits1, fits2, z=0.05, display=False, save=False):
    """
    Reproject and resample fits2 image on fits1
    Parameters
    ----------

    Returns
    -------

    """
    hdu1 = fits.open(fits1)[0]
    hdu2 = fits.open(fits2)[0]

    fix_pp_header(hdu1.header)
    fix_pp_header(hdu2.header)

    fits2_reproj, footprint = reproject_interp(hdu2, hdu1.header)

    if display:
        #fig, (ax1, ax2, ax3) = plt.subplots(1,3, figsize=(18,6))
        fig = plt.figure(figsize=(18,6))

        ax1 = fig.add_subplot(1,3,1, projection=WCS(hdu1.header))
        ax1.imshow(z_scale(hdu1.data, c=z), origin='lower', cmap='Greys_r')
        ax1.coords['ra'].set_axislabel('Right Ascension')
        ax1.coords['dec'].set_axislabel('Declination')
        ax1.set_title(f'Image 1\n{fits1}')
        
        ax2 = fig.add_subplot(1,3,2, projection=WCS(hdu2.header))
        ax2.imshow(z_scale(hdu2.data, c=z), origin='lower', cmap='Greys_r')
        ax2.coords['ra'].set_axislabel('Right Ascension')
        ax2.coords['dec'].set_axislabel('Declination')
        ax2.set_title(f'Image 2\n{fits2}')
        
        ax3 = fig.add_subplot(1,3,3, projection=WCS(hdu1.header))
        try:
            ax3.imshow(z_scale(fits2_reproj, c=z), origin='lower', cmap='Greys_r')
        except IndexError:
            ax3.imshow(fits2_reproj, origin='lower', cmap='Greys_r')
        ax3.coords['ra'].set_axislabel('Right Ascension')
        ax3.coords['dec'].set_axislabel('Declination')
        ax3.set_title('Image 2 reprojected on Image 1')
        
        fig.tight_layout()
        plt.show()
    
    if save:
        wrk_dir = Path(fits2).parent
        Path(wrk_dir/'reprojected').mkdir(parents=True, exist_ok=True)

        wcs_header = WCS(hdu1.header).to_header()
        newhdu = fits.PrimaryHDU(data=fits2_reproj, header=hdu2.header)
        newhdu.header.update(wcs_header)
        newhdu.header['DATE-OBS'] = hdu2.header['DATE-OBS']
        newfname = Path(fits2).parent/'reprojected'/Path(fits2).name
        tqdm.write(f"> Saving reprojected image to {newfname}")
        newhdu.writeto(newfname, overwrite=True)
    
    return fits2_reproj

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description=
                                     "Reproject and resample fits2 image on fits1")

    parser.add_argument('fits1', help='list of reference fits frames', nargs='+')
    parser.add_argument('-f2','--fits2', help='list of fits frame to be reprojected', nargs='+')
    parser.add_argument('-d','--display',
                        help='Display reprojected images',
                        action='store_true')
    parser.add_argument('-s','--save',
                        help='Save reprojected images',
                        action='store_true')

    args = parser.parse_args()

    fits1 = sorted(list(args.fits1))
    fits2 = sorted(list(args.fits2))
    display = args.display
    save = args.save

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #
    warnings.simplefilter('ignore', category=AstropyWarning)

    if len(fits1) > 1 and len(fits1) != len(fits2):
        raise ValueError(f"Number of files dont match : {len(fits1)} vs {len(fits2)}")
    elif len(fits1) == 1: # projecting all fits2 on the same image
        print(f"> Reprojecting {len(fits2)} frames")
        for f2 in tqdm(fits2):
            reproject(fits1[0], f2, display=display, save=save)
    else:
        print(f"> Reprojecting {len(fits2)} frames")
        for f1, f2 in tqdm(zip(fits1, fits2)):
            reproject(f1, f2, display=display, save=save)
