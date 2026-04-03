#!/usr/bin/env python3

""" FITS_INVERT - Invert fits file data

    creation : JUL 2025
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# FITS manipulation
from astropy.io import fits

from pathlib import Path

#
# --- FUNCTIONS ---------------------------------------------------------------
#

# Utils functions

def open_fits(fname):
    hdu = fits.open(str(fname))
    header = hdu[0].header
    data = hdu[0].data
    hdu.close()
    return data, header


def save_fits(fname, data, header):
    header['OLD-NAME'] = fname
    header.comments['OLD-NAME'] = 'Original data inverted by:'
    header.comments['OLD-NAME'] = 'fits_invert.py'
    newhdu = fits.PrimaryHDU(data=data, header=header)
    newfname = f'{fname[:-5]}_inverted.fits'
    newfname = Path(fname).parent/'inverted'/f'{Path(fname).stem}_inverted.fits'
    print(f'> Saving inverted image to  {newfname}')
    newhdu.writeto(newfname, overwrite=True)


def invert(fnames):
    """
    
    """

    wrk_dir = Path(fnames[0]).parent
    Path(wrk_dir/'inverted').mkdir(parents=True, exist_ok=True)

    # Make sure fnames is a list of FITS file names
    if isinstance(fnames, str):
        fnames = [fnames]
    
    # Loop on FITS files : get data and header; remove sky bkg, save to file
    for fname in fnames:
        fname = str(fname)
        data, header = open_fits(fname)
    
        save_fits(fname, -1 * data, header)

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('fnames', help='list of FITS file names', nargs='+')

    args = parser.parse_args()

    fnames = sorted(args.fnames)

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #

    invert(fnames)
