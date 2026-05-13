#!/usr/bin/env python3

""" FITS_CROPPING - Crop FITS images.

    creation : JUL 2023
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# Filesytem paths
from pathlib import Path

# astropy
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import Cutout2D

# Plotting
import matplotlib.pyplot as plt

from image_scaling import z_scale


#
# --- FUNCTIONS ---------------------------------------------------------------
#

# Utils functions

def open_fits(fname):
    hdu = fits.open(fname)
    header = hdu[0].header
    data = hdu[0].data
    hdu.close()
    return data, header


def save_fits(fname, data, header):
    # Create new hdu
    newhdu = fits.PrimaryHDU(data=data, header=header)
    newhdu.writeto(fname, overwrite=True)


def plot_cropping(data, size, position, wcs=None):
    """
    Plot the original image along with the crop region delimations and center
    """

    # Force to plot without projection for now
    wcs = None
    
    figsize = (10, 10)
    color = 'C02'
    if not wcs:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig, ax = plt.subplots(figsize=figsize, subplot_kw={'projection':wcs})

    ax.imshow(z_scale(data, c=0.005), origin='lower', cmap='Greys_r')
    
    # Draw position and cropped region
    ax.plot(position[0], position[1], '+', ms=8, color=color)
    anchor = position[0] - size[0]//2, position[1] - size[1]//2 
    rectangle = plt.Rectangle(anchor, size[0], size[1],
                                 angle=0.0, color=color, lw=1, fill=False)
    ax.add_patch(rectangle)

    txt = f'Position = [{position[0]:.2f}, {position[1]:.2f}] \nSize = {size}'
    ax.text(anchor[0]+5, anchor[1]+5, txt, color=color)

    #ax.coords.grid(True, color='white', ls='solid')
    #overlay = ax.get_coords_overlay('fk5')
    #overlay.grid(color='white', ls='dotted')

    fig.tight_layout()
    plt.show()


def cropping(data, size, position, wcs=None, display=False):
    """
    Array cropping
    """

    # If position not specified, default to the image center
    if not position:
        position = data.shape[1]//2, data.shape[0]//2
    cutout = Cutout2D(data, position=position, size=size, wcs=wcs,
                      fill_value=0, mode='partial')

    if display:
        plot_cropping(data, size, position, wcs=wcs)
    
    if wcs:
        return cutout.data, cutout.wcs
    else:
        return cutout.data
        


def fits_cropping(fname,
                  size,
                  position=None,
                  save=False,
                  verbose=False,
                  display=False):
    """
    Cropping of a FITS image.
    """
    
    data, header = open_fits(fname)
    wcs = WCS(header)

    # If position not specified, default to the image center
    if not position:
        position = data.shape[1]//2, data.shape[0]//2
    # If only one size is specified, use square
    if len(size) == 1:
        size = [size[0],size[0]]

    if verbose:
        print(f'> Position = {position}')
        print(f'> Size = {size}')

    cutout, wcs = cropping(data, size, position, wcs=wcs, display=display)
        
    if save:
        # Indicate old file name in the header
        header['OLD-NAME'] = fname
        header.comments['OLD-NAME'] = 'Cropped by:'
        header.comments['OLD-NAME'] = 'fits_cropping.py'
        # Update the FITS header with the cutout WCS
        try:
            header.update(cutout.wcs.to_header())
        except AttributeError:
            print('WCS not updated')
        # Create new file name
        newfname = f'{fname[:-5]}_cropped.fits'
        print(f'> Saving cropped image to  {newfname}')
        # Save FITS file
        save_fits(newfname, cutout.data, header)
    
    return cutout


#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('fnames', help='list of FITS file names', nargs='+')
    parser.add_argument('-sz','--size', help='Crop size(s)', nargs='+')
    parser.add_argument("-p", "--position",
                        help="Crop position coordinates", nargs='+')  
    parser.add_argument('-v','--verbose',
                        help='Print background stats',
                        action='store_true')
    parser.add_argument('-d','--display',
                        help='Display results',
                        action='store_true')
    parser.add_argument('-s','--save',
                        help='Save results to FITS files',
                        action='store_true')

    args = parser.parse_args()

    fnames = sorted(args.fnames)
    size = [int(sz) for sz in args.size]
    position = args.position
    verbose = args.verbose
    display = args.display
    save = args.save

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #

    # matplotlib style
    try:
        plt.style.use(Path(__file__).resolve().parent/"bmh.mplstyle")
    except OSError:
        print('Custom matplotlib style file not found -> use default')

    if size:
        size = [int(sz) for sz in args.size]
        if len(size) == 1: # If only one size is specified, use square
            size = [size[0],size[0]]    
    if position:
        position = [int(p) for p in position]


    for fname in fnames:

        cutout = fits_cropping(fname,
                                     size,
                                     position,
                                     save=save,
                                     verbose=verbose,
                                     display=display)
