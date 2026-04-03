#!/usr/bin/env python3

""" FITS_BKGSUB - Background subtraction from FITS images.

    creation : JUL 2023
"""

#
# --- IMPORTS -----------------------------------------------------------------
#

# Command line arguments parser
import argparse

# Numerical computing
import numpy as np

# Photutils
from photutils.background import Background2D, MedianBackground, SExtractorBackground
from photutils.segmentation import detect_threshold, detect_sources
from photutils.utils import circular_footprint

# FITS manipulation + sigma clipping + image visualization
from astropy.stats import sigma_clipped_stats, SigmaClip
from astropy.io import fits
from astropy.visualization import SqrtStretch, LogStretch, ZScaleInterval
from astropy.visualization.mpl_normalize import ImageNormalize

# Plotting
import matplotlib.pyplot as plt


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
    header['OLD-NAME'] = fname
    header.comments['OLD-NAME'] = 'Background subtracted by:'
    header.comments['OLD-NAME'] = 'fits_bkgsub.py'
    newhdu = fits.PrimaryHDU(data=data, header=header)
    newfname = f'{fname[:-5]}_bkgsub.fits'
    print(f'> Saving bkgsub image to  {newfname}')
    newhdu.writeto(newfname, overwrite=True)


# Bkg sub on a single array
def bkgsub_array(data,
                 box_size=(50,50), filter_size=(3,3), masking=False,
                 verbose=False, display=False):
    """
    Background subtraction using photutils
    """

    # masking sources
    mask = None
    sigma_clip = SigmaClip(sigma=3.0, maxiters=10)
    if masking:
        threshold = detect_threshold(data, nsigma=3.0, sigma_clip=sigma_clip)
        segment_img = detect_sources(data, threshold, npixels=10)
        footprint = circular_footprint(radius=10)
        mask = segment_img.make_source_mask(footprint=footprint)
    # masking blank data
    coverage_mask = (data == 0)

    # Bkg estimation
    bkg_estimator = MedianBackground()
    #bkg_estimator = SExtractorBackground()

    bkg = Background2D(data,
                       box_size, filter_size=filter_size,
                       sigma_clip=sigma_clip,
                       bkg_estimator=bkg_estimator,
                       mask=mask,
                       coverage_mask=coverage_mask, fill_value=0.0)
    
    if verbose:
        print(f'> Bkg median = {bkg.background_median}')
        print(f'> Bkg RMS median = {bkg.background_rms_median}')

    # Plots
    if display:
        fig, axs = plt.subplots(3, 2, figsize=(12,12))

        #norm = ImageNormalize(stretch=SqrtStretch())
        norm = ImageNormalize(stretch=LogStretch())
        #interval = ZScaleInterval(contrast=0.05)

        # data
        axs[0,0].set_title('Data')
        axs[0,0].imshow(data, norm=norm, origin='lower', cmap='Greys_r',
                        interpolation='nearest')
        # bkg
        axs[1,0].set_title('Background estimation')
        axs[1,0].imshow(bkg.background, origin='lower', cmap='Greys_r',
                        interpolation='nearest')
        # data - bkg
        axs[0,1].set_title('Background subtracted data')
        axs[0,1].imshow(data - bkg.background, norm=norm, origin='lower',
                        cmap='Greys_r', interpolation='nearest')
        # masked  image
        axs[2,0].set_title('Mask')
        mask_img = np.zeros_like(data)
        mask_img[mask] = 1
        axs[2,0].imshow(mask_img, origin='lower', cmap='Greys_r')
        # plot meshes
        axs[2,1].set_title('Meshes')
        axs[2,1].imshow(data, origin='lower', cmap='Greys_r', norm=norm,
        interpolation='nearest')
        bkg.plot_meshes(outlines=True, color='#1f77b4')

        fig.tight_layout()
        plt.show()

    return data-bkg.background, bkg.background


# Bkg sub wrapper for list of fits files
def bkgsub_fits(fnames, save=False,
                box_size=(50,50), filter_size=(3,3),
                masking=False,
                verbose=False,
                display=False):
    """
    Background subtraction using photutils for a list of FITS images.
    """

    # Make sure fnames is a list of FITS file names
    if isinstance(fnames, str):
        fnames = [fnames]
    
    bkgsub_imgs = []
    
    # Loop on FITS files : get data and header; remove sky bkg, save to file
    for fname in fnames:
    
        data, header = open_fits(fname)

        bkgsub_img, bkg = bkgsub_array(data,
                                       box_size=box_size,
                                       filter_size=filter_size,
                                       masking=masking,
                                       verbose=verbose,
                                       display=display)
        
        bkgsub_imgs.append(bkgsub_img)
        
        if save:
            save_fits(fname, bkgsub_img, header)

    return bkgsub_imgs

#
# --- ARGS PARSER -------------------------------------------------------------
#
if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('fnames', help='list of FITS file names', nargs='+')
    parser.add_argument('-b','--box_size',
                        help='Size of boxes on which background is evaluated \
                            (default = 50)',
                        default=50, type=int)
    parser.add_argument('-f','--filter_size',
                        help='Size of filter used (default = 3)',
                        default=3, type=int)
    parser.add_argument('-m','--masking',
                        help='Mask sources',
                        action='store_true')
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
    box_size = (args.box_size, args.box_size)
    filter_size = (args.filter_size, args.filter_size)
    masking = args.masking
    verbose = args.verbose
    display = args.display
    save = args.save

    #
    # --- SCRIPT CODE ---------------------------------------------------------
    #

    bkgsub_img = bkgsub_fits(fnames, save=save,
                            box_size=box_size, filter_size=filter_size, 
                            masking=masking,
                            verbose=verbose,
                            display=display)
