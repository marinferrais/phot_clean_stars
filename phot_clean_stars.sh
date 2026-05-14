#!/bin/bash

 <<'COMMENT_BLOCK'

PHOT_CLEAN_STARS - This script improves photometry in crowded field by
                   subtracting median images to each images to limit star
                   contamination.
    
    author: marin ferrais
    creation : AUG 2025

#
# Usage #######################################################################
#

phot_median_subtraction.sh -rp -sz 600 -z 0.5 -t 00490 -aprad 7 -k 20 -p 40 -solar -s_pp

# 0003I bin 2x2:
phot_median_subtraction.sh -sz 300 -z 1.2 -t 2025_N1 -aprad 3.5 -k 6 -rp

# 0003I bin 1x1:
phot_median_subtraction.sh -sz 300 -z 0.6 -t 2025_N1 -aprad 7 -k 6 -rp


#
# Dependencies ################################################################
#

Photometry Pipelines with custom pp_distill
gif_maker.py
fits_rolling_median_subtraction_PP.py
fits_reproject.py
pp_instru-zp.py
gif_lightcurve.py
obs2dat.py
ffmpeg

#
# TODO ########################################################################
#

Test more k values
Test padding influence
Automatic estimation of minimum padding based on typical FWHM and target speed
Test SWARP sigma clip combination mode
remove zero padding of targetname in obs file?
change epoch number of decimals to 7 ?
Complete dependencies list
Deal with filter and bands (if band differant than filter?)
Use something else than PP to get the instru mag?

COMMENT_BLOCK

#
# #############################################################################
#
set -e  # stop script on errors

# Print outputs to both stdout and logfile.
LOG_FILE="phot_star_clean.out"
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec > >(tee -a "$LOG_FILE") 2>&1  


#
# Args default values #########################################################
#
FITS_FILES=("*.fits") # List of FITS files (dont forget the quotes)
SOLAR=        # solar mode for PP
APRAD=3.5     # PP photometry aperture
APRAD_TAR=    # PP photometry aperture for the target only
FILTER=       # Filter to use for PP calibration (band), if not specified, calibrate to the filter used
K=6           # median selections windows size
PAD=0         # median selections padding for slow targets
VERBOSE=      # verbose mode for median selections
IMGSZ=300     # image cutouts px size
GIFSZ=500     # gif px size
GIFDL=0.5     # gif delay between frames in seconds
GIFPOSX=      # gif x center position in pixel
GIFPOSY=      # gif y center position in pixel
ZOOM=1.2      # PP manident zoom
SKIP_PP=false # skip intial PP run
REPROJ=false  # do residual reprojection (only to compare images so far)
WRK_DIR=      # Working directory (defaut is current directory)


#
# Other arguments not (yet ?) included as command line args ###################
#
GIFF=1    # gif size factor
MAXFLAG=3 # PP source extractor max flag (to not discard data because of star contamination)
#SCALING_TYPE='uni_perct'
SCALING_TYPE='zscale'

#
# Args parsing ################################################################
#
while [[ $# -gt 0 ]]; do
  case "$1" in
    -ff|--fits_files)
      FITS_FILES="$2"
      shift 2
      ;;
    -wd|--wrk_dir)
      WRK_DIR="$2"
      shift 2
      ;;
    -t|--target)
      TARGET="$2"
      shift 2
      ;;
    -solar)
      SOLAR="-solar"
      shift
      ;;
    -aprad)
      APRAD="$2"
      shift 2
      ;;
    -aprad_tar)
      APRAD_TAR="$2"
      shift 2
      ;;
    -filter)
      FILTER="$2"
      shift 2
      ;;
    -sz|--imgsz)
      IMGSZ="$2"
      shift 2
      ;;
    -gsz|--gifsz)
      GIFSZ="$2"
      shift 2
      ;;
    -px|--gifpx)
      GIFPOSX="$2"
      shift 2
      ;;
    -py|--gifpy)
      GIFPOSY="$2"
      shift 2
      ;;
    -dl|--gifdl)
      GIFDL="$2"
      shift 2
      ;;
    -k)
      K="$2"
      shift 2
      ;;
    -p|--pad)
      PAD="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE="-v"
      shift
      ;;
    -z|--zoom)
      ZOOM="$2"
      shift 2
      ;;
    -s_pp | --skip_pp)
      SKIP_PP=true
      shift
      ;;
    -rp | --reproj)
      REPROJ=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

#
# Setting up some variables ###################################################
#

# if no specific aprad for the target, set as the same as for stars
if [[ -z "$APRAD_TAR" ]]; then
  APRAD_TAR=$APRAD
fi

if [[ -z "$WRK_DIR" ]]; then
  WRK_DIR=$PWD
elif [[ "$WRK_DIR" == "../" || "$WRK_DIR" == ".." ]]; then
  WRK_DIR=$(dirname "$PWD")
fi

BASENAME=$(basename "$WRK_DIR")
# if no target specified, try to use current directory name
if [[ -z "$TARGET" ]]; then
  TARGET="${BASENAME%%_*}"
fi

# Targetname modif for 3I
if [[ "$TARGET" == "2025_N1" ]]; then
  TARGET_PP_PHO="ATLAS"
  TARGETNAME="0003I"
else
  TARGET_PP_PHO=$TARGET
  TARGETNAME=$TARGET
fi

# Defining output file names
GIF_OBS=$WRK_DIR/$BASENAME".gif"                       # Gif original images
GIF_MED=$WRK_DIR/$BASENAME"_medians.gif"               # Gif median images 
GIF_RES=$WRK_DIR/$BASENAME"_residuals.gif"             # Gif residual images
GIF_RES_RPRJ=$WRK_DIR/$BASENAME"_residuals_reproj.gif" # Gif residual images reprojected
GIF_RES_COMPA=$WRK_DIR/$BASENAME"_residuals_compa.gif" # Collage gif original + residual images
OBS_MEDSUB=$WRK_DIR/residuals/$BASENAME".obs"          # Median subtracted obs file  
OBS_NOSUB=$WRK_DIR/$BASENAME".obs"                     # Original obs file
GIF_LC=$WRK_DIR/$BASENAME"_lc.gif"                     # Gif comparison lightcurves
GIF_ALL=$WRK_DIR/$BASENAME"_resi-lc.gif"               # Gif lightcurves + original and residual images
#PHO_ZP                                                # PP photometric file original
if [[ "${TARGET_PP_PHO:0:1}" == "0" ]]; then # remove 0 padding in ast number
  PHO_ZP=$WRK_DIR/"photometry_""$((10#$TARGET_PP_PHO))""_*_.dat"
else
  PHO_ZP=$WRK_DIR/"photometry_""$TARGET_PP_PHO""_*_.dat"
fi
PHO_INSTRU=$WRK_DIR/residuals/photometry_manual_target.dat # PP photometric file instrumental


echo ""
echo "#########################################################################"
echo "WRK_DIR   ="$WRK_DIR
echo "### ARGS ################################################################"
echo "BASENAME  =  "$BASENAME
echo "# PP:"
echo "SKIP_PP   =  "$SKIP_PP
echo "TARGET    =  "$TARGET
echo "TARGET_PP_PHO="$TARGET_PP_PHO
echo "TARGETNAME=  "$TARGETNAME
echo "SOLAR     =  "$SOLAR
echo "APRAD     =  "$APRAD
echo "APRAD_TAR =  "$APRAD_TAR
echo "FILTER    =  "$FILTER
echo "# Gifs:"
echo "IMGSZ     =  "$IMGSZ
echo "GIFSZ     =  "$GIFSZ
echo "GIFPOSX   =  "$GIFPOSX
echo "GIFPOSY   =  "$GIFPOSY
echo "GIFDL     =  "$GIFDL
echo "REPROJ    =  "$REPROJ
echo "# Median subtraction:"
echo "K         =  "$K
echo "PAD       =  "$PAD
echo "VERBOSE   =  "$VERBOSE
echo "# Manual indentification"
echo "ZOOM      =  "$ZOOM
echo "#########################################################################"
echo "### OUTPUT FILE NAMES ###################################################"
echo "GIF_OBS =  "$GIF_OBS
echo "GIF_MED =  "$GIF_MED
echo "GIF_RES =  "$GIF_RES
echo "GIF_RES_RPRJ  =  "$GIF_RES_RPRJ
echo "GIF_RES_COMPA =  "$GIF_RES_COMPA
echo "OBS_MEDSUB =  "$OBS_MEDSUB
echo "OBS_NOSUB  =  "$OBS_NOSUB
echo "GIF_LC  =  "$GIF_LC
echo "GIF_ALL =  "$GIF_ALL
echo "#########################################################################"
echo ""
echo $PHO_ZP
echo $PHO_INSTRU

#
# SCRIPT ######################################################################
#


# Run PP on original images, unless skipped # TODO: find out why it messes with the console output ?
if [[ "$SKIP_PP" == false && -z "$FILTER" ]]; then
  pp_run $FITS_FILES -fixed_aprad $APRAD -target $TARGET $SOLAR
elif [[ "$SKIP_PP" == false ]]; then
  pp_run $FITS_FILES -fixed_aprad $APRAD -target $TARGET -filter $FILTER $SOLAR
else
  echo "> Initial pp run skipped"
fi

POS_FILE=$WRK_DIR/positions.dat
# Create gif of original images
if [[ -z "$GIFPOSX" || -z "$GIFPOSY" ]]; then
  gif_maker.py $FITS_FILES -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -n $GIF_OBS -wt -sctype $SCALING_TYPE -aprad $APRAD -app $POS_FILE
else
  gif_maker.py $FITS_FILES -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -n $GIF_OBS -wt -p $GIFPOSX $GIFPOSY -sctype $SCALING_TYPE -aprad $APRAD -app $POS_FILE
fi

# Create median subtracted images (residuals) to remove stars
fits_rolling_median_subtraction_PP.py $FITS_FILES -k $K -km -p $PAD $VERBOSE 

# Create gif of the median frames
if [[ -z "$GIFPOSX" || -z "$GIFPOSY" ]]; then
  gif_maker.py medians/*_median.fits -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -n $GIF_MED  -sctype $SCALING_TYPE
else
  gif_maker.py medians/*_median.fits -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -n $GIF_MED -p $GIFPOSX $GIFPOSY -sctype $SCALING_TYPE
fi

# Remove medians frames to save disk space
rm -r medians

echo "> Moving to residuals directory"
cd residuals/

# Create gif of the median subtracted images (residuals)
if [[ -z "$GIFPOSX" || -z "$GIFPOSY" ]]; then
  gif_maker.py $FITS_FILES -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -d ../ -n $GIF_RES -sctype $SCALING_TYPE
else
  gif_maker.py $FITS_FILES -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -d ../ -n $GIF_RES -p $GIFPOSX $GIFPOSY -sctype $SCALING_TYPE
fi

# Reproject the residual frames on the original images for comparison purposes, unless skipped
if [[ "$REPROJ" == true ]]; then
  fits_reproject.py ../$FITS_FILES -f2 $FITS_FILES -s
  if [[ -z "$GIFPOSX" || -z "$GIFPOSY" ]]; then
    gif_maker.py reprojected/$FITS_FILES -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -d ../ -n $GIF_RES_RPRJ -sctype $SCALING_TYPE -aprad $APRAD_TAR -app $POS_FILE
  else
    gif_maker.py reprojected/$FITS_FILES -sz $IMGSZ -gsz $GIFSZ -dl $GIFDL -d ../ -n $GIF_RES_RPRJ -p $GIFPOSX $GIFPOSY -sctype $SCALING_TYPE -aprad $APRAD_TAR -app $POS_FILE
  fi
  # hstack orginal and residual gifs
  ffmpeg -y -i $GIF_OBS -i $GIF_RES_RPRJ -filter_complex '[0]scale=-1:-1[a];[1]scale=-1:-1[b];[a][b]hstack[v];[v]palettegen=max_colors=256:stats_mode=full[p]' -map '[p]' -update 1 -frames:v 1 palette.png
  ffmpeg -y -i $GIF_OBS -i $GIF_RES_RPRJ -i palette.png -filter_complex '[0]scale=-1:-1[a];[1]scale=-1:-1[b];[a][b]hstack[v];[v][2:v]paletteuse=dither=none' -plays 0 $GIF_RES_COMPA
  rm -r reprojected
else
  echo "> No residual reprojection"
fi

#
# Run PP on the residual frames with manual identification of the target
#

# Fits preparation. We keep the WCS (it is not used after)
pp_prepare $FITS_FILES -keep_wcs 

# Photometry with fixed aperture size
pp_photometry.py $FITS_FILES -aprad $APRAD_TAR

# Writing instrumental mags to database
pp_calibrate $FITS_FILES -instrumental

# Manual identification of the target : a and d to browse images, q to quit
#pp_manident $FITS_FILES -zoom $ZOOM

# Extract photometry from the original images positions
pp_distill $FITS_FILES -mf $MAXFLAG -target manual -positions $POS_FILE


# Combine ZP from original images with instrumental mags from residual fromes
pp_instru-zp.py $PHO_INSTRU -zp $PHO_ZP -v -o $OBS_MEDSUB -t $TARGETNAME
obs2dat.py $OBS_MEDSUB -s

# Create lightcurve gif
GIF_LC_SZ=$(($((GIFSZ * 2)) / 100 )) # lc figure width is 2 times the gifs size
gif_lightcurve.py $OBS_NOSUB $OBS_MEDSUB -dl $GIFDL -n $GIF_LC -sz $GIF_LC_SZ
#Stack lc gif with original images and residuals gif
ffmpeg -y -i $GIF_LC -i $GIF_RES_COMPA -filter_complex "[0:v][1:v]vstack=inputs=2,fps=15,palettegen=stats_mode=full[p]" -map "[p]" palette.png
ffmpeg -y -i $GIF_LC -i $GIF_RES_COMPA -i palette.png -filter_complex "[0:v][1:v]vstack=inputs=2,fps=15[v];[v][2:v]paletteuse=dither=bayer:bayer_scale=5" -plays 0 $GIF_ALL

# Open the final obs file in gedit
echo "> Opening final OBS file in gedit : ""$OBS_MEDSUB"
gedit $OBS_MEDSUB

# Open final comparison gif
eog $GIF_ALL

