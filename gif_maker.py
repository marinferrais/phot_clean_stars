#!/usr/bin/env python3

from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from astropy.time import Time
from astropy.nddata import Cutout2D

import io
import imageio.v2 as imageio
from tqdm import tqdm
import numpy as np
import argparse
import matplotlib.pyplot as plt
from pathlib import Path
import rocks

from fits_asteroid import get_fits_infos, get_astpx
from fits_bkgsub import bkgsub_array
from image_scaling import z_scale, minmax_scale, manual_scale


def get_text(fits_infos_list):
    # get infos to be written on the gif : object name, telescope, times
    target = fits_infos_list[0][0]
    rocksid = rocks.id(target)
    if np.isnan(rocksid[1]):
        target = rocksid[0]
    else:
        target = f"({rocksid[1]}) {rocksid[0]}"

    code2name = {'I40': 'TRAPPIST-South', 'Z53': 'TRAPPIST-North',
                 'Z25': 'Artemis', '691':'Spacewatch-0.9m',
                 'W39':'Robinson Observatory',
                 }
    telescope = code2name.get(fits_infos_list[0][1], fits_infos_list[0][1])

    jd = np.array(fits_infos_list)[:,2]   
    dates = Time(jd, format='jd').isot

    return target, telescope, dates


def add_text(fig, ax, target, telescope, date, i, n):
    # Add text infos on the gif : object name, telescope, time, image counter

    # fontsize scaled to figure width in pixels
    fontsize = fig.get_size_inches()[0] * fig.dpi * 0.03 # 3% of figure width
    line_height = (fontsize / 72) / fig.get_size_inches()[1]

    ax.text(
        0.5, 0.98,
        target,
        transform=ax.transAxes,
        fontsize=fontsize,
        ha='center',
        va='top',
        color='white',
        #fontweight='bold',
    )
    ax.text(
        0.02, 0.02,
        telescope,
        transform=ax.transAxes,
        fontsize=fontsize,
        ha='left',
        va='bottom',
        color='white',
    )
    ax.text(
        0.98, 0.02,
        date,
        transform=ax.transAxes,
        fontsize=fontsize,
        ha='right',
        va='bottom',
        color='white',
    )
    ax.text(
        0.98, 0.02 + line_height * 1.2,
        f"{i+1} / {n}",
        transform=ax.transAxes,
        fontsize=fontsize,
        ha='right',
        va='bottom',
        color='white',
    )


def get_images(fnames, size=None, position=None, coordinates=None, bkgsub=False,
               get_ast_pos=True, file_ap_pos=None):
    """
    Read FITS file, extract cutout, subtract background, get asteroid position
    on the images, get photometric aperture positions on the images
    """

    data_list = []
    fits_infos_list = []
    pos_ast_list = []

    # Crop center from RA-Dec coordinates
    if coordinates:
        if len(coordinates[0]) == 3 and len(coordinates[1]) == 3:
            ra, dec = coordinates
            ra = 15*(ra[0] + ra[1]/60 + ra[2]/3600)
            dec = dec[0] + dec[1]/60 + dec[2]/3600

    # Read apeture positions file
    if file_ap_pos:
        ap_coord = np.genfromtxt(file_ap_pos, dtype=[('filename', 'S50'),
                                                    ('ra', float),
                                                    ('dec', float),
                                                    ('MJD', float)],
                                                    names=True)

    ap_pos_list = []
    aprads = []
    get_pos = False # not sure what this is for ...
    coord_horizons = []
    for i, fname in tqdm(enumerate(fnames), desc='Prepare images'):
        data, header, fits_infos = get_fits_infos(fname)
        if 'APRAD' in header.keys():
            aprads.append(header['APRAD'])
        wcs = WCS(header)
        if coordinates and get_pos:
            x, y = wcs.world_to_pixel(SkyCoord(ra=ra, dec=dec, unit="deg"))
            pos = [float(x), float(y)]
            pos_ast = get_astpx(data, fits_infos, wcs, centroid=False, display=False)
            if size:
                pos_ast = np.array(pos_ast) - np.array(pos) + np.array(size)//2
            pos_ast[1] = size[1]//2 - pos_ast[1] + size[1]//2 # Flip y  TODO: take care of meridian flip
        elif not position and get_pos:
            pos = get_astpx(data, fits_infos, wcs, centroid=False, display=False)
            pos_ast = pos
        else:
            pos = position
        
        if get_pos:
            pos_ast_list.append(pos_ast)

        if get_ast_pos and (not position):
            data, header, fits_infos = get_fits_infos(fname)
            wcs = WCS(header)
            ra, dec, x, y = get_astpx(data,
                                  fits_infos,
                                  wcs, 
                                  centroid=False,
                                  display=False)
            pos = x,y

        # Background subtraction
        if bkgsub:
            data = bkgsub_array(data, display=False)[0]
        # Cropping
        if size or pos:
            if not size:
                size = data.shape
            if not pos:
                pos = data.shape[1]//2, data.shape[0]//2
            cutout = Cutout2D(data, position=pos, size=size, wcs=wcs,
                              fill_value=0, mode='partial')
            data, wcs = cutout.data, cutout.wcs
        
        # Convert aperture coordinates (RA-Dec) to  image coordinates (pixels)
        if file_ap_pos:
            x_ap, y_ap = wcs.world_to_pixel(SkyCoord(ra=ap_coord['RA'][i], dec=ap_coord['Dec'][i], unit="deg"))
            y_ap = data.shape[0] - y_ap
            ap_pos_list.append([x_ap, y_ap])
        
        data_list.append(data)
        fits_infos_list.append(fits_infos)

    return data_list, fits_infos_list, pos_ast_list, ap_pos_list, aprads


def arrays_to_gif_mpl(frames, gif_path, fits_infos_list, duration=100, loop=0, 
                       cmap='gray', gif_size=None, dpi=100,
                       ap_pos_list=None, aprads=None,
                       write_text=None):
    """
    Create a GIF using matplotlib's imshow renderer — same rendering as imshow.
    
    Parameters
    ----------
    frames   : list of 2D numpy arrays
    gif_path : str — output path
    duration : ms per frame
    cmap     : colormap (default 'gray')
    """
    
    # Convert pixel size to figsize if size is provided
    # pixels = figsize * dpi
    if gif_size is not None:
        figsize = (gif_size[0] / dpi, gif_size[1] / dpi)
    elif gif_size is None:
        figsize = (frames[0].shape[1] / dpi, frames[0].shape[0] / dpi)

    if write_text:
        target, telescope, dates = get_text(fits_infos_list)
        n = len(dates)

    rendered_frames = []
    for i, arr in tqdm(enumerate(frames), desc='Image to gif'):
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        ax.imshow(arr, cmap=cmap,
                  origin='lower',
                  interpolation='none')
        
        if write_text:
            add_text(fig, ax, target, telescope, dates[i], i, n)
        
        if ap_pos_list:
            from matplotlib.patches import Circle
            x, y = ap_pos_list[i][0], ap_pos_list[i][1]
            circle = Circle((x, y), aprads[i], color='C0', fill=False, linewidth=1)
            ax.add_patch(circle)

        ax.axis('off')
        plt.tight_layout(pad=0)

        # Render figure to numpy array via buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        rendered_frames.append(imageio.imread(buf))

    # Save as GIF
    imageio.mimsave(gif_path, rendered_frames, duration=duration/1000, loop=loop)

def scale_images(data_list, scaling_type='z_scale', z=0.05):
    #print(scaling_type)
    if scaling_type == 'zscale_uni':
        z_scale_limits_inf = []
        z_scale_limits_sup = []
        for data in data_list:
            limits = z_scale(data, c=z, verbose=False, return_limits=True)[1]
            z_scale_limits_inf.append(limits[0])
            z_scale_limits_sup.append(limits[1])
        z_scale_limit_inf = np.median(z_scale_limits_inf)
        z_scale_limit_sup = np.median(z_scale_limits_sup)
        data_scaled_list = [manual_scale(data, vmin=z_scale_limit_inf, vmax=z_scale_limit_sup)
                            for data in data_list]
    elif scaling_type == 'zscale':
        data_scaled_list = [z_scale(data, c=z)
                            for data in data_list]
    elif scaling_type == 'uni_perct':
        data_scaled_list = [manual_scale(np.nan_to_num(data, nan=0.0),
                                         vmin=np.percentile(data[data != 0], 5),
                                         vmax=np.percentile(data[data != 0], 99))
                            for data in data_list]
    else:
        data_scaled_list = [data for data in data_list]

    return data_scaled_list

def make_gif(fnames, destination, filename, z=0.05, delay=0.2,
                 size=None, gif_size=None, position=None, coordinates=None, bkgsub=False,
                 write_text=False, scaling_type='zscale', get_ast_pos=True,
                 file_ap_pos=None, aprad=None):
    """
    """

    # Gif output directory and name
    destination = Path(destination)
    destination.mkdir(exist_ok=True)
    if filename == 'dir':
        filename = f"{str(Path(fnames[0]).absolute().parent).split('/')[-1]}"
    filename = Path(filename)
    if filename.suffix != '.gif':
        filename = filename.with_suffix('.gif')
    gif_path = destination/filename

    # read images, get cutouts, get metadata
    get_images_res = get_images(fnames,
                                size=size, position=position, coordinates=coordinates,
                                bkgsub=bkgsub, get_ast_pos=get_ast_pos, file_ap_pos=file_ap_pos)
    data_list, fits_infos_list, pos_list, ap_pos_list, aprads = get_images_res

    if aprad: # overwrite headers aprad if one is given
        aprads = [aprad] * len(fnames)

    # Image scaling
    data_scaled_list = scale_images(data_list, scaling_type=scaling_type, z=z)

    arrays_to_gif_mpl(data_scaled_list, gif_path, fits_infos_list, duration=delay*1000, gif_size=gif_size, ap_pos_list=ap_pos_list, aprads=aprads, write_text=write_text)

    
    print(f"> Gif saved to {gif_path}")



if __name__ == '__main__':

    # command line arguments
    parser = argparse.ArgumentParser(description='Make gif from FITS images')

    parser.add_argument("fnames", help='input FITS files', nargs='+')
    parser.add_argument("-d", "--destination", help='destination folder',
                        default=".", type=str)
    parser.add_argument("-n", "--gifname", help='output gif name',
                        default="mygif", type=str)
    parser.add_argument("-i", "--images",
                        help='enable creation of the individual PNG images\
                              instead of the gif', action='store_true')
    parser.add_argument("-st", "--stack",
                        help='enable creation of stacked image\
                              instead of the gif', action='store_true')
    parser.add_argument("-z", "--z_scale", help='z scaling factor (default=0.05)',
                        default=0.05, type=float)
    parser.add_argument("-dl", "--delay", help='delay between images (default=0.2s)',
                        default=0.2, type=float)
    parser.add_argument("-s", "--skip", help='skip a certain number of images',
                        default=1, type=int)
    parser.add_argument('-sz','--size', help='Crop size(s)', nargs='+', type=int)
    parser.add_argument('-gsz','--gif_size', help='Gif size size(s)', nargs='+', type=int)
    parser.add_argument("-p", "--position",
                        help="Crop position coordinates", nargs='+') 
    parser.add_argument('-w','--warnings_enabled',
                        help='Enable Astropy warnings',
                        action='store_true')
    parser.add_argument('-b','--bkgsub',
                        help='Enable bkg subtraction',
                        action='store_true')
    parser.add_argument('-wt','--write_text',
                        help='Enable text infos on gif',
                        action='store_true')
    parser.add_argument('-sctype','--scaling_type',
                        help='Type of image scaling to use',
                        choices=['zscale', 'zscale_uni', 'uni_perct'],
                        default='zscale')
    parser.add_argument("-app", "--file_ap_pos", help='output gif name',
                        default="", type=str)
    parser.add_argument("-aprad", "--aprad", help='Photometric aperture radius',
                        default=None, type=float)


    args = parser.parse_args()

    fnames = sorted(args.fnames)
    destination = args.destination
    gifname = args.gifname
    z = args.z_scale
    dl = args.delay
    s = args.skip
    size = args.size
    gif_size = args.gif_size
    position = args.position
    bkgsub = args.bkgsub
    warnings_enabled = args.warnings_enabled
    scaling_type = args.scaling_type

    images = args.images
    stack = args.stack
    write_text = args.write_text

    file_ap_pos = args.file_ap_pos
    aprad = args.aprad

    if not warnings_enabled:
        import warnings
        from astropy.utils.exceptions import AstropyWarning
        warnings.simplefilter('ignore', category=AstropyWarning)

    if size:
        if len(size) == 1: # If only one size is specified, use square
            size = [size[0], size[0]]
    if gif_size:
        if len(gif_size) == 1: # If only one size is specified, use square
            gif_size = [gif_size[0], gif_size[0]]
    if position:
        position = [int(p) for p in position]

    make_gif(fnames[::s], destination, gifname,
                     z=z, delay=dl,
                     bkgsub=bkgsub,
                     size=size,
                     gif_size=gif_size,
                     position=position,
                     write_text=write_text,
                     get_ast_pos=True, # TODO put in args cmd line
                     scaling_type=scaling_type,
                     #coordinates=[(21,32,22), (-0,-14,-29)]
                     file_ap_pos=file_ap_pos,
                     aprad=aprad
                     )
