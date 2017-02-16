"""
Generate artificial waveforms of weakly electric fish.

The two main functions are

generate_wavefish()
generate_pulsefish()

for generating EODs of wave-type and pulse_type electric fish, respectively.

The following functions use the two functions to generate waveforms of specific fishes:

generate_alepto(): mimicks the wave-type fish Apteronotus leptorhynchus, 
generate_eigenmannia(): mimicks the wave-type fish Eigenmannia, 

generate_monophasic_pulses(): mimicks a monophasic pulsefish,
generate_biphasic_pulses(): mimicks a biphasic pulsefish,
generate_triphasic_pulses(): mimicks a triphasic pulsefish.

The frequency traces of communication signals are generated by

chirps_frequency() for chirps, and
rises_frequency() for rises.

The returned frequency of these functions can then be directly passed on
to generate_wavefish() for generating a frequency modulated EOD waveform.
"""

import numpy as np


def generate_wavefish(frequency=100.0, samplerate=44100., duration=1., noise_std=0.05,
                      amplitudes=1.0, phases=0.0):
    """
    Generate EOD of a wave-type fish.

    The waveform is constructed by superimposing sinewaves of integral multiples of
    the fundamental frequency - the fundamental and its harmonics.
    The fundamental frequency of the EOD is given by frequency. The amplitude of the
    fundamental is given by the first element in amplitudes. The amplitudes and
    relative phases of higher harmonics are give by optional further elements of
    the amplitudes and phases lists.

    The generated waveform is duration seconds long and is sampled with samplerate Hertz.
    Gaussian white noise with a standard deviation of noise_std is added to the generated
    waveform.

    Parameters
    ----------
    frequency: float or array of floats
        EOD frequency of the fish in Hz. Either fixed number or array for
        time-dependent frequencies.
    samplerate: float
        Sampling rate in Hz.
    duration: float
        Duration of the generated data in seconds. Only used if frequency is float.
    noise_std: float
        Standard deviation of additive Gaussian white noise.
    amplitudes: float or list of floats
        Amplitudes of fundamental and optional harmonics.
    phases: float or list of floats
        Relative phases of fundamental and optional harmonics in radians.

    Returns
    -------
    data: array of floats
        Generated data of a wave-type fish.

    Raises
    ------
    IndexError: amplitudes and phases differ in length.
    """
    
    # compute phase:
    if np.isscalar(frequency):
        phase = np.arange(0, duration, 1./samplerate)
        phase *= frequency
    else:
        phase = np.cumsum(frequency)/samplerate
    # fix amplitudes and phases:
    if np.isscalar(amplitudes):
        amplitudes = [amplitudes]
    if np.isscalar(phases):
        phases = [phases]
    if len(amplitudes) != len(phases):
        raise IndexError('need exactly as many phases as amplitudes')
    # generate EOD:
    data = np.zeros(len(phase))
    for har, (ampl, phi) in enumerate(zip(amplitudes, phases)):
        data += ampl * np.sin(2*np.pi*(har+1)*phase+phi)
    # add noise:
    data += noise_std * np.random.randn(len(data))
    return data


def generate_alepto(frequency=100.0, samplerate=44100., duration=1., noise_std=0.01):
    """Generate EOD of a Apteronotus leptorhynchus.

    See generate_wavefish() for details.
    """
    return generate_wavefish(frequency=frequency, samplerate=samplerate, duration=duration,
                             noise_std=noise_std, amplitudes=[1.0, 0.5, 0.1, 0.01, 0.001],
                             phases=[0.0, 0.0, 0.0, 0.0, 0.0])


def generate_eigenmannia(frequency=100.0, samplerate=44100., duration=1., noise_std=0.01):
    """Generate EOD of an Eigenmannia.

    See generate_wavefish() for details.
    """
    return generate_wavefish(frequency=frequency, samplerate=samplerate, duration=duration,
                             noise_std=noise_std, amplitudes=[1.0, 0.25, 0.0, 0.01],
                             phases=[0.0, 0.5*np.pi, 0.0, 0.0])


def chirps_frequency(eodf=100.0, samplerate=44100., duration=1.,
                     chirp_freq=5.0, chirp_size=100.0, chirp_width=0.01, chirp_kurtosis=1.0):
    """
    Generate frequency trace with chirps.

    A chirp is modeled as a Gaussian frequency modulation.

    Parameters
    ----------
    eodf: float
        EOD frequency of the fish in Hz.
    samplerate: float
        Sampling rate in Hz.
    duration: float
        Duration of the generated data in seconds.
    chirp_freq: float
        Frequency of occurance of chirps in Hertz.
    chirp_size: float
        Size of the chirp (frequency increase above eodf) in Hertz.
    chirp_width: float
        Width of the chirp at 10% height in seconds.
    chirp_kurtosis (float):
        Shape of the chirp. =1: Gaussian, >1: more rectangular, <1: more peaked.

    Returns
    -------
    data: array of floats
        Generated frequency trace that can be passed on to generate_wavefish().
    """

    # baseline eod frequency:
    frequency = eodf * np.ones(int(duration*samplerate))
    # time points for chirps:
    chirp_period = 1.0/chirp_freq
    chirp_times = np.arange(0.5*chirp_period, duration, chirp_period)
    # chirp frequency waveform:
    chirp_t = np.arange(-2.0*chirp_width, 2.0*chirp_width, 1./samplerate)
    chirp_sig = 0.5*chirp_width / (2.0*np.log(10.0))**(0.5/chirp_kurtosis)
    chirp = chirp_size * np.exp(-0.5*((chirp_t/chirp_sig)**2.0)**chirp_kurtosis)
    # add chirps on baseline eodf:
    for c in chirp_times:
        index = int(c*samplerate)
        if index+len(chirp) > len(frequency):
            break
        frequency[index:index+len(chirp)] += chirp
    return frequency


def rises_frequency(eodf=100.0, samplerate=44100., duration=1.,
                    rise_freq=0.1, rise_size=10.0, rise_tau=1.0, decay_tau=10.0):
    """
    Generate frequency trace with rises.

    A rise is modeled as a double exponential frequency modulation.

    Parameters
    ----------
    eodf: float
        EOD frequency of the fish in Hz.
    samplerate: float
        Sampling rate in Hz.
    duration: float
        Duration of the generated data in seconds.
    rise_freq: float
        Frequency of occurance of rises in Hertz.
    rise_size: float
        Size of the rise (frequency increase above eodf) in Hertz.
    rise_tau: float
        Time constant of the frequency increase of the rise in seconds.
    decay_tau: float
        Time constant of the frequency decay of the rise in seconds.

    Returns
    -------
    data: array of floats
        Generated frequency trace that can be passed on to generate_wavefish().
    """

    # baseline eod frequency:
    frequency = eodf * np.ones(int(duration*samplerate))
    # time points for rises:
    rise_period = 1.0/rise_freq
    rise_times = np.arange(0.5*rise_period, duration, rise_period)
    # rise frequency waveform:
    rise_t = np.arange(0.0, 5.0*decay_tau, 1./samplerate)
    rise = rise_size * (1.0-np.exp(-rise_t/rise_tau)) * np.exp(-rise_t/decay_tau)
    # add rises on baseline eodf:
    for r in rise_times:
        index = int(r*samplerate)
        if index+len(rise) > len(frequency):
            rise_index = len(frequency)-index
            frequency[index:index+rise_index] += rise[:rise_index]
            break
        else:
            frequency[index:index+len(rise)] += rise
    return frequency


def generate_pulsefish(frequency=100.0, samplerate=44100., duration=1., noise_std=0.01,
                       jitter_cv=0.1, peak_stds=0.001, peak_amplitudes=1.0, peak_times=0.0):
    """
    Generate EOD of a pulse-type fish.

    Pulses are spaced by 1/frequency, jittered as determined by jitter_cv. Each pulse is
    a combination of Gaussian peaks, whose widths, amplitudes, and positions are given by
    their standard deviation peak_stds, peak_amplitudes, and peak_times, respectively.

    The generated waveform is duration seconds long and is sampled with samplerate Hertz.
    Gaussian white noise with a standard deviation of noise_std is added to the generated
    pulse train.

    Parameters
    ----------
    frequency: float
        EOD frequency of the fish in Hz.
    samplerate: float
        Sampling Rate in Hz.
    duration: float
        Duration of the generated data in seconds.
    noise_std: float
        Standard deviation of additive Gaussian white noise.
    jitter_cv: float
        Gaussian distributed jitter of pulse times as coefficient of variation of inter-pulse intervals.
    peak_stds: float or list of floats
        Standard deviation of Gaussian shaped peaks in seconds.
    peak_amplitudes: float or list of floats
        Amplitude of each peak (positive and negative).
    peak_times: float or list of floats
        Position of each Gaussian peak in seconds.

    Returns
    -------
    data: array of floats
        Generated data of a pulse-type fish.

    Raises
    ------
    IndexError: peak_stds or peak_amplitudes or peak_times differ in length.
    """

    # make sure peak properties are in a list:
    if np.isscalar(peak_stds):
        peak_stds = [peak_stds]
    if np.isscalar(peak_amplitudes):
        peak_amplitudes = [peak_amplitudes]
    if np.isscalar(peak_times):
        peak_times = [peak_times]
    if len(peak_stds) != len(peak_amplitudes) or len(peak_stds) != len(peak_times):
        raise IndexError('need exactly as many peak_stds as peak_amplitudes and peak_times')

    # time axis for single pulse:
    min_time_inx = np.argmin(peak_times)
    max_time_inx = np.argmax(peak_times)
    x = np.arange(-4.*peak_stds[min_time_inx] + peak_times[min_time_inx],
                  4.*peak_stds[max_time_inx] + peak_times[max_time_inx], 1.0/samplerate)
    pulse_duration = x[-1] - x[0]
    
    # generate a single pulse:
    pulse = np.zeros(len(x))
    for time, ampl, std in zip(peak_times, peak_amplitudes, peak_stds):
        pulse += ampl * np.exp(-0.5*((x-time)/std)**2) 

    # paste the pulse into the noise floor:
    time = np.arange(0, duration, 1. / samplerate)
    data = np.random.randn(len(time)) * noise_std
    period = 1.0/frequency
    jitter_std = period * jitter_cv
    first_pulse = np.max(pulse_duration, 3.0*jitter_std)
    pulse_times = np.arange(first_pulse, duration, period )
    pulse_times += np.random.randn(len(pulse_times)) * jitter_std
    pulse_indices = np.round(pulse_times * samplerate).astype(np.int)
    for inx in pulse_indices[(pulse_indices >= 0) & (pulse_indices < len(data)-len(pulse)-1)]:
        data[inx:inx + len(pulse)] += pulse

    return data


def generate_monophasic_pulses(frequency=100.0, samplerate=44100., duration=1.,
                               noise_std=0.01, jitter_cv=0.1):
    """Generate EOD of a monophasic pulse-type fish.

    See generate_pulsefish() for details.
    """
    return generate_pulsefish(frequency=frequency, samplerate=samplerate, duration=duration,
                              noise_std=noise_std, jitter_cv=jitter_cv,
                              peak_stds=0.0003, peak_amplitudes=1.0, peak_times=0.0)


def generate_biphasic_pulses(frequency=100.0, samplerate=44100., duration=1.,
                              noise_std=0.01, jitter_cv=0.1):
    """Generate EOD of a biphasic pulse-type fish.

    See generate_pulsefish() for details.
    """
    return generate_pulsefish(frequency=frequency, samplerate=samplerate, duration=duration,
                              noise_std=noise_std, jitter_cv=jitter_cv,
                              peak_stds=[0.0001, 0.0002],
                              peak_amplitudes=[1.0, -0.3],
                              peak_times=[0.0, 0.0003])


def generate_triphasic_pulses(frequency=100.0, samplerate=44100., duration=1.,
                              noise_std=0.01, jitter_cv=0.1):
    """Generate EOD of a triphasic pulse-type fish.

    See generate_pulsefish() for details.
    """
    return generate_pulsefish(frequency=frequency, samplerate=samplerate, duration=duration,
                              noise_std=noise_std, jitter_cv=jitter_cv,
                              peak_stds=[0.0001, 0.0001, 0.0002],
                              peak_amplitudes=[1.0, -0.8, 0.1],
                              peak_times=[0.0, 0.00015, 0.0004])


def main():
    import sys
    import matplotlib.pyplot as plt
    from audioio import write_audio
    try:
        input_ = raw_input
    except NameError:
        input_ = input

    def read(prompt, default=None, dtype=str, min=None, max=None):
        if default is not None:
            prompt += ' (%s): ' % default
        while True:
            s = input_(prompt)
            if len(s) == 0 and default is not None:
                s = default
            if len(s) > 0:
                try:
                    x = dtype(s)
                except ValueError:
                    x = None
                if x is not None:
                    if min is not None and x < min:
                        continue
                    if max is not None and x > max:
                        continue
                    return x

    def select(prompt, default, options, descriptions):
        print(prompt)
        for o, d in zip(options, descriptions):
            print('  [%s] %s' % (o, d))
        sprompt = '  Select'
        if default is not None:
            sprompt += ' (%s): ' % default
        while True:
            s = input_(sprompt).lower()
            if len(s) == 0:
                s = default
            if s in options:
                return s
            
    
    if len(sys.argv) > 1:
        if len(sys.argv) == 2 or sys.argv[1] != '-s':
            print('usage: fakefish [-h] [-s audiofile]')
            print('')
            print('Without arguments, run a demo for illustrating fakefish functionality.')
            print('')
            print('-s audiofile: writes audiofile with user defined simulated electric fishes.')
            print('')
            print('by bendalab (2017)')
        else:
            # generate file:
            audiofile = sys.argv[2]
            samplerate = read('Sampling rate in Hz', '44100', float, 1.0)
            duration = read('Duration in seconds', '10', float, 0.001)
            nfish = read('Number of fish', '1', int, 1)
            eodt = 'a'
            eodf = 800.0
            eoda = 1.0
            eodsig = 'n'
            pulse_jitter = 0.1
            chirp_freq = 5.0
            chirp_size = 100.0
            chirp_width = 0.01
            chirp_kurtosis = 1.0            
            rise_freq = 0.1
            rise_size = 10.0
            rise_tau = 1.0
            rise_decay_tau = 10.0
            for k in range(nfish):
                print('')
                fish = 'Fish %d: ' % (k+1)
                eodt = select(fish + 'EOD type', eodt, ['a', 'e', '1', '2', '3'],
                              ['Apteronotus', 'Eigenmannia',
                               'monophasic pulse', 'biphasic pulse', 'triphasic pulse'])
                eodf = read(fish + 'EOD frequency in Hz', '%g'%eodf, float, 1.0, 3000.0)
                eoda = read(fish + 'EOD amplitude', '%g'%eoda, float, 0.0, 10.0)
                if eodt in 'ae':
                    eodsig = select(fish + 'Add communication signals', eodsig, ['n', 'c', 'r'],
                              ['fixed EOD', 'chirps', 'rises'])
                    eodfreq = eodf
                    if eodsig == 'c':
                        chirp_freq = read('Number of chirps per second', '%g'%chirp_freq, float, 0.001)
                        chirp_size = read('Size of chirp in Hz', '%g'%chirp_size, float, 1.0)
                        chirp_width = 0.001*read('Width of chirp in ms', '%g'%(1000.0*chirp_width), float, 1.0)
                        eodfreq = chirps_frequency(eodf, samplerate, duration,
                                                   chirp_freq, chirp_size, chirp_width, chirp_kurtosis)
                    elif eodsig == 'r':
                        rise_freq = read('Number of rises per second', '%g'%rise_freq, float, 0.00001)
                        rise_size = read('Size of rise in Hz', '%g'%rise_size, float, 0.01)
                        rise_tau = read('Time-constant of rise onset in seconds', '%g'%rise_tau, float, 0.01)
                        rise_decay_tau = read('Time-constant of rise decay in seconds', '%g'%rise_decay_tau, float, 0.01)
                        eodfreq = rises_frequency(eodf, samplerate, duration,
                                                  rise_freq, rise_size, rise_tau, rise_decay_tau)
                    if eodt == 'a':
                        fishdata = eoda*generate_alepto(eodfreq, samplerate, duration=duration)
                    elif eodt == 'e':
                        fishdata = eoda*generate_eigenmannia(eodfreq, samplerate, duration=duration)
                else:
                    pulse_jitter = read(fish + 'CV of pulse jitter', '%g'%pulse_jitter, float, 0.0, 2.0)
                    if eodt == '1':
                        fishdata = eoda*generate_monophasic_pulses(eodf, samplerate, duration,
                                                                   jitter_cv=pulse_jitter)
                    elif eodt == '2':
                        fishdata = eoda*generate_biphasic_pulses(eodf, samplerate, duration,
                                                                 jitter_cv=pulse_jitter)
                    elif eodt == '3':
                        fishdata = eoda*generate_triphasic_pulses(eodf, samplerate, duration,
                                                                  jitter_cv=pulse_jitter)
                if k == 0:
                    data = fishdata
                else:
                    data += fishdata

            maxdata = np.max(np.abs(data))
            write_audio(audiofile, 0.9*data/maxdata, samplerate)
            print('\nWrote fakefish data to file "%s".' % audiofile)
    
    else:
        # demo:
        samplerate = 40000.  # in Hz
        duration = 10.0       # in sec

        inset_len = 0.01  # in sec
        inset_indices = int(inset_len*samplerate)
        ws_fac = 0.1  # whitespace factor or ylim (between 0. and 1.; preferably a small number)

        # generate data:
        time = np.arange(0, duration, 1./samplerate)

        eodf = 400.0
        #eodf = 500.0 - time/duration*400.0
        wavefish = generate_wavefish(eodf, samplerate, duration=duration, noise_std=0.02, 
                                     amplitudes=[1.0, 0.5, 0.1, 0.0001],
                                     phases=[0.0, 0.0, 0.0, 0.0])
        eodf = 650.0
        # wavefish = generate_alepto(eodf, samplerate, duration=duration)
        wavefish += 0.5*generate_eigenmannia(eodf, samplerate, duration=duration)

        pulsefish = generate_pulsefish(80., samplerate, duration=duration,
                                       noise_std=0.02, jitter_cv=0.1,
                                       peak_stds=[0.0001, 0.0002],
                                       peak_amplitudes=[1.0, -0.3],
                                       peak_times=[0.0, 0.0003])
        # pulsefish = generate_monophasic_pulses(80., samplerate, duration=duration)
        # pulsefish = generate_biphasic_pulses(80., samplerate, duration=duration)
        # pulsefish = generate_triphasic_pulses(80., samplerate, duration=duration)

        fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(19, 10))

        # get proper wavefish ylim
        ymin = np.min(wavefish)
        ymax = np.max(wavefish)
        dy = ws_fac*(ymax - ymin)
        ymin -= dy
        ymax += dy

        # complete wavefish:
        ax[0][0].set_title('Wavefish')
        ax[0][0].set_ylim(ymin, ymax)
        ax[0][0].plot(time, wavefish)

        # wavefish zoom in:
        ax[0][1].set_title('Wavefish ZOOM IN')
        ax[0][1].set_ylim(ymin, ymax)
        ax[0][1].plot(time[:inset_indices], wavefish[:inset_indices], '-o')

        # get proper pulsefish ylim
        ymin = np.min(pulsefish)
        ymax = np.max(pulsefish)
        dy = ws_fac*(ymax - ymin)
        ymin -= dy
        ymax += dy

        # complete pulsefish:
        ax[1][0].set_title('Pulsefish')
        ax[1][0].set_ylim(ymin, ymax)
        ax[1][0].plot(time, pulsefish)

        # pulsefish zoom in:
        ax[1][1].set_title('Pulsefish ZOOM IN')
        ax[1][1].set_ylim(ymin, ymax)
        ax[1][1].plot(time[:inset_indices/2], pulsefish[:inset_indices/2], '-o')

        for row in ax:
            for c_ax in row:
                c_ax.set_xlabel('Time [sec]')
                c_ax.set_ylabel('Amplitude [a.u.]')

        plt.tight_layout()

        # chirps:
        chirps_freq = chirps_frequency(600.0, samplerate, duration=duration, chirp_kurtosis=1.0)
        chirps_data = generate_alepto(chirps_freq, samplerate)

        # rises:
        rises_freq = rises_frequency(600.0, samplerate, duration=duration, rise_size=20.0)
        rises_data = generate_alepto(rises_freq, samplerate)

        nfft = 256
        fig, ax = plt.subplots(nrows=2, ncols=1, figsize=(19, 10))
        ax[0].set_title('Chirps')
        ax[0].specgram(chirps_data, Fs=samplerate, NFFT=nfft, noverlap=nfft//16)
        time = np.arange(len(chirps_freq))/samplerate
        ax[0].plot(time[:-nfft/2], chirps_freq[nfft/2:], '-k', lw=2)
        ax[0].set_ylim(0.0, 3000.0)
        ax[0].set_ylabel('Frequency [Hz]')

        nfft = 4096
        ax[1].set_title('Rises')
        ax[1].specgram(rises_data, Fs=samplerate, NFFT=nfft, noverlap=nfft//2)
        time = np.arange(len(rises_freq))/samplerate
        ax[1].plot(time[:-nfft/4], rises_freq[nfft/4:], '-k', lw=2)
        ax[1].set_ylim(500.0, 700.0)
        ax[1].set_ylabel('Frequency [Hz]')
        ax[1].set_xlabel('Time [s]')
        plt.tight_layout()

        plt.show()

            
if __name__ == '__main__':
    main()
