__author__ = 'juan'
# Imports
import os
import numpy as np
import wave
import sys
from scipy.signal import butter, filtfilt
from IPython import embed

def peakdet(v, delta, x=None):
    """
    Converted from MATLAB script at http://billauer.co.il/peakdet.html
    Returns two arrays
    function [maxtab, mintab]=peakdet(v, delta, x)
    %PEAKDET Detect peaks in a vector
    % [MAXTAB, MINTAB] = PEAKDET(V, DELTA) finds the local
    % maxima and minima ("peaks") in the vector V.
    % MAXTAB and MINTAB consists of two columns. Column 1
    % contains indices in V, and column 2 the found values.
    %
    % With [MAXTAB, MINTAB] = PEAKDET(V, DELTA, X) the indices
    % in MAXTAB and MINTAB are replaced with the corresponding
    % X-values.
    %
    % A point is considered a maximum peak if it has the maximal
    % value, and was preceded (to the left) by a value lower by
    % DELTA.
    % Eli Billauer, 3.4.05 (Explicitly not copyrighted).
    % This function is released to the public domain; Any use is allowed.
    """
    maxtab = []
    maxidx = []

    mintab = []
    minidx = []

    if x is None:
        x = np.arange(len(v), dtype=int)

    v = np.asarray(v)

    if len(v) != len(x):
        sys.exit('Input vectors v and x must have same length')

    if not np.isscalar(delta):
        sys.exit('Input argument delta must be a scalar')

    if delta <= 0:
        sys.exit('Input argument delta must be positive')

    mn, mx = np.Inf, -np.Inf
    mnpos, mxpos = np.NaN, np.NaN

    lookformax = True

    for i in np.arange(len(v)):
        this = v[i]
        if this > mx:
            mx = this
            mxpos = x[i]

        if this < mn:
            mn = this
            mnpos = x[i]


        if lookformax:
            if this < mx-delta:
                maxtab.append(mx)
                maxidx.append(mxpos)
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn+delta:
                mintab.append(mn)
                minidx.append(mnpos)
                mx = this
                mxpos = x[i]
                lookformax = True

    return np.array(maxtab), np.array(maxidx), np.array(mintab), np.array(minidx)


def butter_lowpass(highcut, fs, order=5):
    nyq = 0.5 * fs
    high = highcut / nyq
    b, a = butter(order, high, btype='low')
    return b, a


def butter_lowpass_filter(data, highcut, fs, order=5):
    b, a = butter_lowpass(highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y


def load_trace(modfile, analysis_length=30):
    """ Loads modified .wav file from avconv with the library wave. This function returns an array with the time trace,
    an array with the amplitude values with the same length as the time-trace-array and finally it returns the sample-
    rate as a float. In order to accelerate the code, the default analysis-length are
    the first 30 seconds of the sound file.
    """
    recording = wave.open(modfile)
    sample_rate = recording.getframerate()
    frames_to_read = analysis_length * sample_rate  # read not more than the first 30 seconds
    data = np.fromstring(recording.readframes(frames_to_read), np.int16).astype(float)  # read data
    data -= np.mean(data)
    time_length = float(data.size) / sample_rate
    t_trace = np.linspace(0.0, time_length, num=data.size)
    return t_trace, data, sample_rate


def conv_to_single_ch_audio(audiofile):
    """ This function uses the software avconv to convert the current file to a single channel audio wav-file
    (or mp3-file), with which we can work afterwards using the package wave. Returns the name of the modified
    file as a string

    :rtype : str
    :param audiofile: sound-file that was recorded
    """

    base, ext = os.path.splitext(audiofile)
    base = base.split('/')[-1]
    new_mod_filename = 'recording_' + base + '_mod.wav'
    os.system('avconv -i {0:s} -ac 1 -y -acodec pcm_s16le {1:s}'.format(audiofile, new_mod_filename))
    return new_mod_filename


def create_outp_folder(filepath, out_path='.'):

    field_folder = '/'.join(filepath.split('.')[-2].split('/')[-3:-1])

    paths = {1: out_path, 2: field_folder}

    for k in paths.keys():
        if paths[k][-1] != '/':
            paths[k] += '/'
    new_folder = ''.join(paths.values())

    return new_folder
