"""
Track wave-type electric fish frequencies over time.

fish_tracker(): load data and track fish.
"""
import sys
import os
import argparse
import numpy as np
from .version import __version__
from .configfile import ConfigFile
from .dataloader import open_data
from .powerspectrum import spectrogram, next_power_of_two
from .harmonicgroups import add_psd_peak_detection_config, add_harmonic_groups_config
from .harmonicgroups import harmonic_groups_args, psd_peak_detection_args
from .harmonicgroups import harmonic_groups, fundamental_freqs, plot_psd_harmonic_groups
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
# TODO: update to numpy doc style!


def extract_fundamentals(data, samplerate, start_time=0.0, end_time=-1.0,
                         data_snippet_secs=60.0,
                         nffts_per_psd=4, fresolution=0.5, overlap_frac=.9,
                         plot_harmonic_groups=False, verbose=0, **kwargs):
    """
    For a long data array calculates spectograms of small data snippets, computes PSDs, extracts harmonic groups and
    extracts fundamental frequncies.

    :param data: (array) raw data.
    :param samplerate: (int) samplerate of data.
    :param start_time: (int) analyze data from this time on (in seconds).  XXX this should be a float!!!! Internally I would use indices.
    :param end_time: (int) stop analysis at this time (in seconds). If -1 then analyse to the end of the data. XXX TODO this should be a float!!!! Internally I would use indices.
    :param data_snippet_secs: (float) duration of data snipped processed at once in seconds. Necessary because of memory issues.
    :param nffts_per_psd: (int) number of nffts used for calculating one psd.
    :param fresolution: (float) frequency resolution for the spectrogram.
    :param overlap_frac: (float) overlap of the nffts (0 = no overlap; 1 = total overlap).
    :param verbose: (int) with increasing value provides more output on console.
    :param kwargs: further arguments are passed on to harmonic_groups().
    :return all_fundamentals: (list) containing arrays with the fundamentals frequencies of fishes detected at a certain time.
    :return all_times: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    """
    all_fundamentals = []
    all_times = np.array([])

    if end_time < 0.0:
        end_time = len(data)/samplerate

    nfft = next_power_of_two(samplerate / fresolution)
    if len(data.shape) > 1:
        channels = range(data.shape[1])
    else:
        channels = range(1)

    while start_time < int((len(data)- data_snippet_secs*samplerate) / samplerate) or int(start_time) == 0:
        if verbose >= 3:
            print('Minute %.2f' % (start_time/60))

        for channel in channels:
            # print(channel)
            if len(channels) > 1:
                tmp_data = data[int(start_time*samplerate) : int((start_time+data_snippet_secs)*samplerate), channel]
            else:
                tmp_data = data[int(start_time*samplerate) : int((start_time+data_snippet_secs)*samplerate)]

            # spectrogram
            spectrum, freqs, time = spectrogram(tmp_data, samplerate, fresolution=fresolution, overlap_frac=overlap_frac)  # nfft window = 2 sec

            # psd and fish fundamentals frequency detection
            tmp_power = [np.array([]) for i in range(len(time)-(nffts_per_psd-1))]
            for t in range(len(time)-(nffts_per_psd-1)):
                # power = np.mean(spectrum[:, t:t+nffts_per_psd], axis=1)
                tmp_power[t] = np.mean(spectrum[:, t:t+nffts_per_psd], axis=1)
            if channel == 0:
                power = tmp_power
            else:
                for t in range(len(power)):
                    power[t] += tmp_power[t]

        all_times = np.concatenate((all_times, time[:-(nffts_per_psd-1)] + start_time))

        for p in range(len(power)):
            fishlist, _, mains, all_freqs, good_freqs, _, _, _ = harmonic_groups(freqs, power[p], **kwargs)
            fundamentals = fundamental_freqs(fishlist)
            all_fundamentals.append(fundamentals)
            if plot_harmonic_groups:
                fig = plt.figure()
                ax = fig.add_subplot(1, 1, 1)
                plot_psd_harmonic_groups(ax, freqs, power[p], fishlist, mains,
                                         all_freqs, good_freqs, max_freq=3000.0)
                ax.set_title('time = %gmin' % ((start_time+0.0)/60.0))  # XXX TODO plus what???
                plt.show()

        if (len(all_times) % ((len(time) - (nffts_per_psd-1)) * 30)) > -1 and (
                    len(all_times) % ((len(time) - (nffts_per_psd-1)) * 30)) < 1:
            if verbose >= 3:
                print('Minute %.0f' % (start_time/60))

        start_time += time[-nffts_per_psd] - (0.5 -(1-overlap_frac)) * nfft / samplerate


        if end_time > 0:
            if start_time >= end_time:
                if verbose >= 3:
                    print('End time reached!')
                break

    return all_fundamentals, all_times


def first_level_fish_sorting(all_fundamentals, base_name, all_times, prim_time_tolerance=5., freq_tolerance = .5,
                             save_original_fishes=False, output_folder = '.', verbose=0):
    """
    Sorts fundamental frequencies of wave-type electric fish detected at certain timestamps to fishes.

    There is an array of fundamental frequencies for every timestamp (all_fundamentals). Each of these frequencies is
    compared to the last frequency of already detected fishes (last_fish_fundamentals). If the frequency difference
    between the new frequency and one or multiple already detected fishes the frequency is appended to the array
    containing all frequencies of the fish (fishes) that has been absent for the shortest period of time. If the
    frequency doesn't fit to one fish, a new fish array is created. If a fish has not been detected at one time-step
    a NaN is added to this fish array.

    The result is for each fish a array containing frequencies or nans with the same length than the time array
    (all_times). These fish arrays can be saved as .npy file to access the code after the time demanding step.

    :param all_fundamentals: (list) containing arrays with the fundamentals frequencies of fishes detected at a certain time.
    :param base_name: (string) filename.
    :param all_times: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    :param prim_time_tolerance: (int) time in minutes from when a certain fish is no longer tracked.
    :param freq_tolerance: (float) maximum frequency difference to assign a frequency to a certain fish.
    :param save_original_fishes: (boolean) if True saves the sorted fishes after the first level of fish sorting.
    :param verbose: (int) with increasing value provides more shell output.
    :return fishes: (list) containing arrays of sorted fish frequencies. Each array represents one fish.
    """
    def clean_up(fishes, last_fish_fundamentals, end_nans):
        """
        Delete fish arrays with too little data points to reduce memory usage.

        :param fishes: (list) containing arrays of sorted fish frequencies. Each array represents one fish.
        :param last_fish_fundamentals: (list) contains for every fish in fishes the last detected fundamental frequency.
        :param end_nans: (list) for every fish contains the counts of nans since the last fundamental detection.
        :return: fishes: (list) cleaned up input list.
        :return: last_fish_fundamentals: (list) cleaned up input list.
        :return: end_nans: (list) cleaned up input list.
        """
        for fish in reversed(range(len(fishes))):
            if len(np.array(fishes[fish])[~np.isnan(fishes[fish])]) <= 10:
                fishes.pop(fish)
                last_fish_fundamentals.pop(fish)
                end_nans.pop(fish)

        return fishes, last_fish_fundamentals, end_nans

    detection_time_diff = all_times[1] - all_times[0]
    dpm = 60. / detection_time_diff  # detections per minutes

    fishes = [np.full(len(all_fundamentals)+1, np.nan)]
    fishes[0][0] = 0.
    last_fish_fundamentals = [ 0. ]
    end_nans = [0]

    # for every list of fundamentals ...
    clean_up_idx = int(30 * dpm)

    for enu, fundamentals in enumerate(all_fundamentals):
        if enu == clean_up_idx:
            if verbose >= 3:
                print('cleaning up ...')
            fishes, last_fish_fundamentals, end_nans = clean_up(fishes, last_fish_fundamentals, end_nans)
            clean_up_idx += int(30 * dpm)

        for idx in range(len(fundamentals)):
            diff = np.abs(np.asarray(last_fish_fundamentals) - fundamentals[idx])
            sorted_diff_idx = np.argsort(diff)
            tolerated_diff_idx = sorted_diff_idx[diff[sorted_diff_idx] < freq_tolerance]

            last_detect_of_tolerated = np.array(end_nans)[tolerated_diff_idx]

            if len(tolerated_diff_idx) == 0:
                fishes.append(np.full(len(all_fundamentals)+1, np.nan))
                fishes[-1][enu+1] = fundamentals[idx]
                last_fish_fundamentals.append(fundamentals[idx])
                end_nans.append(0)
            else:
                found = False
                for i in tolerated_diff_idx[np.argsort(last_detect_of_tolerated)]:
                    if np.isnan(fishes[i][enu+1]):
                        fishes[i][enu+1] = fundamentals[idx]
                        last_fish_fundamentals[i] = fundamentals[idx]
                        end_nans[i] = 0
                        found = True
                        break
                if not found:
                    fishes.append(np.full(len(all_fundamentals)+1, np.nan))
                    fishes[-1][enu+1] = fundamentals[idx]
                    last_fish_fundamentals.append(fundamentals[idx])
                    end_nans.append(0)

        for fish in range(len(fishes)):
            if end_nans[fish] >= prim_time_tolerance * dpm:
                last_fish_fundamentals[fish] = 0.

            if np.isnan(fishes[fish][enu+1]):
                end_nans[fish] += 1
    if verbose >= 3:
        print('cleaning up ...')
    fishes, last_fish_fundamentals, end_nans = clean_up(fishes, last_fish_fundamentals, end_nans)
    # reshape everything to arrays
    for fish in range(len(fishes)):
        fishes[fish] = fishes[fish][1:]

    # if not removed be clean_up(): remove first fish because it has been used for the first comparison !
    if fishes[0][0] == 0.:
        fishes.pop(0)

    if save_original_fishes:
        print('saving')
        np.save(os.path.join(output_folder, base_name) + '-fishes.npy', np.asarray(fishes))
        np.save(os.path.join(output_folder, base_name) + '-times.npy', all_times)

    return np.asarray(fishes)


def detect_rises(fishes, all_times, rise_f_th = .5, verbose = 0):
    """
    Detects rises in frequency arrays that belong to a certain fish.

    Single rises are detected with the function 'detect_single_rises()' and get appended to a list.
    When the function 'detect_single_rises()' detects a rise it returns some data about the rise and continues seaching
    for rises at that index in the data where the detected rise ended. (While-loop)

    :param fishes: (array) containing arrays of sorted fish frequencies. Each array represents one fish.
    :param all_times: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    :param rise_f_th: (float) minimum frequency difference between peak and base of a rise to be detected as such.
    :return all_rises: (list) contains a list for each fish which each contains a list for every detected rise. In this
                       last list there are two arrays containing the frequency and the index of start and end of the rise.
                       all_rises[ fish ][ rise ][ [idx_start, idx_end], [freq_start, freq_end] ]
    """

    def detect_single_rise(fish, non_nan_idx, rise_f_th, dpm):
        """
        Detects a single rise in an array of fish frequencies.

        At first and an index of the array is detected from where on in the next 10 seconds every frequency is lower.
        This index is at first assumed as the peak of the rise.
        Afterwards and index is searched for from where on in the next 30 seconds every frequency is larger.
        This index is assumed as the end of the rise.
        The other possibility to get an end index of a rise is when the frequency doesnt drop any longer.

        If during the process of finding the end and the peak of the rise, the time difference between those indices
        rise above a time threshold (10 min) or the frequency rises above the assumed peak frequency of the rise, both
        indices are withdrawn and the seach continues.

        When both a peak and a end index are detected the frequency difference between those indices have to be larger
        than n * frequency threshold. n is defined by the time difference between peak and end of the rise.

        In the end index and frequency of rise peak and end are part if the return as well as the non_nan_indices of the
        fish array that are larger than the end index of the detected rise.

        :param fish: (array) sorted fish frequencies-
        :param non_nan_idx: (array) Indices where the fish array is not Nan.
        :param f_th: (float) minimum frequency difference between peak and base of a rise to be detected as such.
        :param dpm: (float) delta-t of the fish array.
        :return: index and frequency of start and end of one detected rise.
                 [[start_idx, end_idx], [start_freq, end_freq]]
        :return: Indices where the fish array is not Nan only containing those values larger than the end_idx of the
                 detected rise.
        """
        loop_idxs = np.arange(len(non_nan_idx[non_nan_idx <= non_nan_idx[-1] - dpm/ 60. * 10]))
        for i in loop_idxs:
            help_idx = np.arange(len(non_nan_idx))[non_nan_idx < non_nan_idx[i] + dpm / 60. * 10][-1]

            idxs = non_nan_idx[i+1:help_idx]
            if len(idxs) < dpm / 60. * 1.:
                continue

            if len(fish[idxs][fish[idxs] < fish[non_nan_idx[i]]]) == len(fish[idxs]):
                for j in loop_idxs[loop_idxs > i]:

                    if fish[non_nan_idx[j]] >= fish[non_nan_idx[i]]:
                        break

                    if non_nan_idx[j] - non_nan_idx[i] >= dpm * 10.:
                        break

                    help_idx2 = np.arange(len(non_nan_idx))[non_nan_idx < non_nan_idx[j] + dpm / 60. * 30][-1]
                    idxs2 = non_nan_idx[j+1:help_idx2]

                    last_possibe = False
                    if fish[non_nan_idx[j]] - np.median(fish[idxs2]) < 0.05:
                        last_possibe = True

                    if len(fish[idxs2][fish[idxs2] >= fish[non_nan_idx[j]]]) == len(fish[idxs2]) or non_nan_idx[j] == non_nan_idx[-1] or last_possibe:
                        freq_th = rise_f_th + ((non_nan_idx[j] - non_nan_idx[i]) *1.) // (dpm /60. *30) * rise_f_th
                        if fish[non_nan_idx[i]] - fish[non_nan_idx[j]] >= freq_th:
                            nnans_befor_start = non_nan_idx[(non_nan_idx > non_nan_idx[i] - dpm / 60 *10) & (non_nan_idx <= non_nan_idx[i])]
                            diff_nnans_before = np.append([nnans_befor_start[0] - (non_nan_idx[i] - dpm / 60 * 10)],np.diff(nnans_befor_start))
                            if len(diff_nnans_before[diff_nnans_before >= dpm / 60 * 3]) > 0:
                                new_start_idx = nnans_befor_start[diff_nnans_before >= dpm / 60 * 3][-1]
                                return [[new_start_idx, non_nan_idx[j]], [fish[new_start_idx], fish[non_nan_idx[j]]]] , non_nan_idx[j+1:]

                            return [[non_nan_idx[i], non_nan_idx[j]], [fish[non_nan_idx[i]], fish[non_nan_idx[j]]]], non_nan_idx[j+1:]
                        else:
                            break
        return [[], []], [non_nan_idx[-1]]

    detection_time_diff = all_times[1] - all_times[0]
    dpm = 60. / detection_time_diff
    all_rises = []
    progress = '0.00'
    if verbose >= 3:
        print('Progress:')
    for enu, fish in enumerate(fishes):
        if verbose >= 3:
            if ('%.2f' % (enu * 1.0 / len(fishes))) != progress:
                print('%.2f' % (enu * 1.0 / len(fishes)))
                progress = ('%.2f' % (enu * 1.0 / len(fishes)))
        non_nan_idx = np.arange(len(fish))[~np.isnan(fish)]
        fish_rises = []
        while non_nan_idx[-1] - non_nan_idx[0] > (dpm / 60. * 10) + 1:
            rise_data, non_nan_idx = detect_single_rise(fish, non_nan_idx, rise_f_th, dpm)
            fish_rises.append(rise_data)
        if not fish_rises == []:
            if fish_rises[-1][0] == []:
                fish_rises.pop(-1)
        all_rises.append(fish_rises)

    return all_rises


def combine_fishes(fishes, all_times, all_rises, max_time_tolerance = 10., f_th = 5.):
    """
    Combines array of electric fish fundamental frequencies which, based on frequency difference and time of occurrence
    likely belong to the same fish.

    Every fish is compared to the fishes that appeared before this fish. If the time of occurrence of two fishes overlap
    or differ by less than a certain time tolerance (10 min.) for each of these fishes a compare index is determined.
    For the fish that second this compare index is either the index of the end of a rise (when the fish array begins
    with a rise) of the first index of frequency detection (when the fish array doesn't begin with a rise). For the fish
    that occurred first the compare index is the first index of detection before the compare index of the second fish.

    If the frequency of the two fishes at the compare indices differ by less than the frequency threshold and the counts
    of detections at the same time is below threshold  a 'distance value' is calculated
    (frequency difference + alpha * time difference oc occur index). These 'distance values' are saved in a matrix.
    After all this matrix contains the 'distance values' for every fish to all other fishes of Nans if the fishes are
    not combinable. Ever fish and its 'distant values' to all other fishes is represented by a row in the matrix.
    (possible_combination_all_fish[fish][compare_fish] = 'distance value' between fish and compare_fish).

    In the next step the fish arrays get combined. Therefore the minimum 'distance value' in the whole matrix is located.
    The index of this value match the fishes that fit together the best. The values of the second fish (fish) get
    transfered into the array of the first fish (comp_fish). Furthermore in the 'distance value' matrix the values that
    pointed to the second fish now point to the first fish. Since the second fish can't anymore point to another fish
    its row in the 'distance value' matrix gets replaced the an array full of nans.
    This process is repeated until this 'distance value' matrix only consists of Nans.
    When a fish is combined with another its rise data also gets transfered.

    In the end the list of fish frequency arrays gets cleaned up as well as the rise array. (Resulting from the sorting
    process the fishes array contains arrays only consisting of Nans. These get deleated.)

    :param fishes: (array) containing arrays of sorted fish frequencies. Each array represents one fish.
    :param all_times: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    :param all_rises: (list) contains a list for each fish which each contains a list for every detected rise. In this
                      last list there are two arrays containing the frequency and the index of start and end of the rise.
                      all_rises[ fish ][ rise ][ [idx_start, idx_end], [freq_start, freq_end] ]
    :param max_time_tolerance: (float) maximum time difference in min. between two fishes to allow combination.
    :param f_th: (float) maximum frequency difference between two fishes to allow combination
    :return fishes: (array) containing arrays of sorted fish frequencies. Each array represents one fish.
    :return all_rises: (list) contains a list for each fish which each contains a list for every detected rise. In this
                       last list there are two arrays containing the frequency and the index of start and end of the rise.
                       all_rises[ fish ][ rise ][ [idx_start, idx_end], [freq_start, freq_end] ]
    """
    detection_time_diff = all_times[1] - all_times[0]
    dpm = 60. / detection_time_diff  # detections per minutes

    occure_idx = []
    delete_idx = []
    possible_combinations_all_fish = np.array([np.full(len(fishes), np.nan) for i in range(len(fishes))])

    for fish in range(len(fishes)):
        non_nan_idx = np.arange(len(fishes[fish]))[~np.isnan(fishes[fish])]
        first_and_last_idx = np.array([non_nan_idx[0], non_nan_idx[-1]])
        occure_idx.append(first_and_last_idx)

    occure_order = np.argsort(np.array([occure_idx[i][0] for i in range(len(fishes))]))

    for fish in reversed(occure_order):
        possible_freq_combinations = np.full(len(fishes), np.nan)
        possible_idx_combinations = np.full(len(fishes), np.nan)
        possible_combinations = np.full(len(fishes), np.nan)

        for comp_fish in reversed(occure_order[:np.where(occure_order == fish)[0][0]]):

            combinable = False
            if occure_idx[fish][0] > occure_idx[comp_fish][0] and occure_idx[fish][0] < occure_idx[comp_fish][1]:
                combinable = True
                comp_fish_nnans_idxs = np.arange(len(fishes[comp_fish]))[~np.isnan(fishes[comp_fish])]
                if all_rises[fish] != []:
                    if occure_idx[fish][0] in [all_rises[fish][i][0][0] for i in range(len(all_rises[fish]))]:
                        x = np.where( np.array([all_rises[fish][i][0][0] for i in range(len(all_rises[fish]))]) == occure_idx[fish][0])[0][0]
                        compare_idxs = [all_rises[fish][x][0][1], comp_fish_nnans_idxs[comp_fish_nnans_idxs < all_rises[fish][x][0][1]][-1]]
                    else:
                        compare_idxs = [occure_idx[fish][0], comp_fish_nnans_idxs[comp_fish_nnans_idxs < occure_idx[fish][0]][-1]]
                else:
                    compare_idxs = [occure_idx[fish][0], comp_fish_nnans_idxs[comp_fish_nnans_idxs < occure_idx[fish][0]][-1]]

            elif occure_idx[fish][0] > occure_idx[comp_fish][1] and occure_idx[fish][0] - occure_idx[comp_fish][1] < max_time_tolerance * dpm:
                combinable = True
                if all_rises[fish] != []:
                    if occure_idx[fish][0] in [all_rises[fish][i][0][0] for i in range(len(all_rises[fish]))]:
                        x = np.where( np.array([all_rises[fish][i][0][0] for i in range(len(all_rises[fish]))]) == occure_idx[fish][0])[0][0]
                        compare_idxs = [all_rises[fish][x][0][1], occure_idx[comp_fish][1]]
                    else:
                        compare_idxs = [occure_idx[fish][0], occure_idx[comp_fish][1]]
                else:
                    compare_idxs = [occure_idx[fish][0], occure_idx[comp_fish][1]]

            if combinable:
                alpha = 0.01 # alpha cant be larger ... to many mistakes !!!
                if np.abs(fishes[fish][compare_idxs[0]] - fishes[comp_fish][compare_idxs[1]]) <= f_th:
                    nan_test = fishes[fish] + fishes[comp_fish]
                    if len(nan_test[~np.isnan(nan_test)]) <= 20:
                        possible_freq_combinations[comp_fish] = np.abs(
                            [fishes[fish][compare_idxs[0]] - fishes[comp_fish][compare_idxs[1]]])
                        possible_idx_combinations[comp_fish] = np.abs([compare_idxs[0] - compare_idxs[1]])

                        possible_combinations[comp_fish] = possible_freq_combinations[comp_fish] + possible_idx_combinations[comp_fish] / (dpm / 60.) * alpha

                        # ax.plot([compare_idxs[0], compare_idxs[1]], [fishes[fish][compare_idxs[0]], fishes[comp_fish][compare_idxs[1]]], '-', color = 'red')

            if comp_fish == 0 and len(possible_freq_combinations[~np.isnan(possible_freq_combinations)]) > 0:
                possible_combinations_all_fish[fish] = possible_combinations

    combining_finished = False
    while combining_finished == False:
        if np.size(possible_combinations_all_fish[~np.isnan(possible_combinations_all_fish)]) == 0:
            combining_finished = True
            continue

        fish = np.where(possible_combinations_all_fish == np.min(possible_combinations_all_fish[~np.isnan(possible_combinations_all_fish)]))[0][0]
        comp_fish = np.where(possible_combinations_all_fish == np.min(possible_combinations_all_fish[~np.isnan(possible_combinations_all_fish)]))[1][0]

        nan_test2 = fishes[fish] +  fishes[comp_fish]
        if len(nan_test2[~np.isnan(nan_test2)]) >= 20:
            possible_combinations_all_fish[fish][comp_fish] = np.nan
            if np.size(possible_combinations_all_fish[~np.isnan(possible_combinations_all_fish)]) == 0:
                combining_finished = True
            continue

        fishes[comp_fish][~np.isnan(fishes[fish])] = fishes[fish][~np.isnan(fishes[fish])]
        fishes[fish] = np.full(len(fishes[fish]), np.nan)

        # clean up possible_combination all fish
        for i in range(len(possible_combinations_all_fish)):
            if not np.isnan(possible_combinations_all_fish[i][fish]):
                if np.isnan(possible_combinations_all_fish[i][comp_fish]):
                    possible_combinations_all_fish[i][comp_fish] = possible_combinations_all_fish[i][fish]
                    possible_combinations_all_fish[i][fish] = np.nan

                elif possible_combinations_all_fish[i][fish] < possible_combinations_all_fish[i][comp_fish]:
                    possible_combinations_all_fish[i][comp_fish] = possible_combinations_all_fish[i][fish]
                    possible_combinations_all_fish[i][fish] = np.nan
                else:
                    possible_combinations_all_fish[i][fish] = np.nan
        possible_combinations_all_fish[fish] = np.full(len(possible_combinations_all_fish[fish]), np.nan)

        if all_rises[fish] != []:
            for rise in range(len(all_rises[fish])):
                all_rises[comp_fish].append(all_rises[fish][rise])
        all_rises[fish] = []

        if np.size(possible_combinations_all_fish[~np.isnan(possible_combinations_all_fish)]) == 0:
            combining_finished = True

    # for i in range(len(fishes)):
    #     ax.plot(np.arange(len(fishes[i]))[~np.isnan(fishes[i])], fishes[i][~np.isnan(fishes[i])], color= np.random.rand(3, 1), marker='.')
    # plt.show()

    for fish in reversed(range(len(fishes))):
        if len(fishes[fish][~np.isnan(fishes[fish])]) == 0:
            delete_idx.append(fish)
            all_rises.pop(fish)

    return_idxs = np.setdiff1d(np.arange(len(fishes)), np.array(delete_idx))

    return fishes[return_idxs], all_rises


def exclude_fishes(fishes, all_times, min_occure_time = 1.):
    """
    Delete fishes that are present for a to short period of time.

    :param fishes: (list) containing arrays of sorted fish frequencies. Each array represents one fish.
    :param all_times: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    :param min_occure_time (int) minimum duration a fish has to be available to not get excluded.
    :return fishes: (array) containing arrays of sorted fish frequencies. Each array represents one fish.
    """
    keep_idx = []
    detection_time_diff = all_times[1] - all_times[0]
    dpm = 60. / detection_time_diff # detections per minute

    for fish in range(len(fishes)):
        if len(fishes[fish][~np.isnan(fishes[fish])]) >= min_occure_time * dpm:
            keep_idx.append(fish)

    return np.asarray(fishes)[keep_idx]


def cut_at_rises(fishes, all_rises):
    """
    Cuts fish arrays at detected rise peaks. For each rise two fish arrays are created with the same length as the
    original fish array.

    This step is necessary because of wrong detections resulting from rises of fishes.

    :param fishes: (array) containing arrays of sorted fish frequencies. Each array represents one fish.
    :param all_rises: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    :return: (array) containing arrays of sorted fish frequencies. Each array represents one fish.
    """
    new_fishes = []
    delete_idx = []
    for fish in reversed(range(len(fishes))):

        for rise in reversed(range(len(all_rises[fish]))):
            cut_idx = all_rises[fish][rise][0][0]
            new_fishes.append(np.full(len(fishes[fish]), np.nan))
            new_fishes[-1][cut_idx:] = fishes[fish][cut_idx:]
            fishes[fish][cut_idx:] = np.full(len(fishes[fish][cut_idx:]), np.nan)
            all_rises.append([all_rises[fish][rise]])
            all_rises[fish].pop(rise)
    for fish in reversed(range(len(fishes))):
        if len(fishes[fish][~np.isnan(fishes[fish])]) <= 10:
            delete_idx.append(fish)
            all_rises.pop(fish)
    return_idx = np.setdiff1d(np.arange(len(fishes)), np.array(delete_idx))

    if len(new_fishes) == 0:
        return fishes, all_rises
    else:
        return np.append(fishes[return_idx], new_fishes, axis=0), all_rises
    # return np.append(fishes[return_idx], new_fishes, axis=0), all_rises


def save_data(fishes, all_times, all_rises, base_name, output_folder):
    np.save(os.path.join(output_folder, base_name) + '-final_fishes.npy', np.asarray(fishes))
    np.save(os.path.join(output_folder, base_name) + '-final_times.npy', all_times)
    np.save(os.path.join(output_folder, base_name) + '-final_rises.npy', np.asarray(all_rises))


def plot_fishes(fishes, all_times, all_rises, base_name, save_plot, output_folder):
    """
    Plot shows the detected fish fundamental frequencies plotted against the time in hours.

    :param fishes: (list) containing arrays of sorted fish frequencies. Each array represents one fish.
    :param all_times: (array) containing time stamps of frequency detection. (  len(all_times) == len(fishes[xy])  )
    """
    fig, ax = plt.subplots(facecolor='white', figsize=(11.6, 8.2))
    if all_times[-1] <= 120:
        time_factor = 1.
    elif all_times[-1] > 120 and all_times[-1] < 7200:
        time_factor = 60.
    else:
        time_factor = 3600.

    for fish in range(len(fishes)):
        color = np.random.rand(3, 1)
        ax.plot(all_times[~np.isnan(fishes[fish])] / time_factor, fishes[fish][~np.isnan(fishes[fish])], color=color, marker='.')

    legend_in = False
    for fish in range(len(all_rises)):
        for rise in all_rises[fish]:
            if rise[1][0] - rise[1][1] > 1.5:
                if legend_in == False:
                    ax.plot(all_times[rise[0][0]] / time_factor, rise[1][0], 'o', color='red', markersize= 7,
                            markerfacecolor='None', label='rise begin')
                    ax.plot(all_times[rise[0][1]] / time_factor, rise[1][1], 's', color='green', markersize= 7,
                            markerfacecolor='None', label='rise end')
                    legend_in = True
                    plt.legend(loc=1, numpoints=1, frameon=False, fontsize = 12)
                else:
                    ax.plot(all_times[rise[0][0]] / time_factor, rise[1][0], 'o', color='red', markersize=7,
                            markerfacecolor='None')
                    ax.plot(all_times[rise[0][1]] / time_factor, rise[1][1], 's', color='green', markersize=7,
                            markerfacecolor='None')

    maxy = np.max(np.array([np.mean(fishes[fish][~np.isnan(fishes[fish])]) for fish in range(len(fishes))]))
    miny = np.min(np.array([np.mean(fishes[fish][~np.isnan(fishes[fish])]) for fish in range(len(fishes))]))

    plt.ylim([miny-150, maxy+150])
    plt.ylabel('Frequency [Hz]', fontsize=14)
    if time_factor == 1.:
        plt.xlabel('Time [sec]', fontsize=14)
    elif time_factor == 60.:
        plt.xlabel('Time [min]', fontsize=14)
    else:
        plt.xlabel('Time [h]', fontsize=14)
    plt.title(base_name, fontsize=16)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()

    if save_plot:
        plt.savefig(os.path.join(output_folder, base_name))
        plt.close(fig)
    else:
        plt.show()


def add_tracker_config(cfg, data_snipped_secs = 60., nffts_per_psd = 4, fresolution = 0.5, overlap_frac = .9,
                       freq_tolerance = 0.5, rise_f_th = 0.5, prim_time_tolerance = 5., max_time_tolerance = 10., f_th=5.):
    """ Add parameter needed for fish_tracker() as
    a new section to a configuration.

    Parameters
    ----------
    cfg: ConfigFile
        the configuration
    data_snipped_secs: float
         duration of data snipped processed at once in seconds.
    nffts_per_psd: int
        nffts used for powerspectrum analysis.
    fresolution: float
        frequency resoltution of the spectrogram.
    overlap_frac: float
        overlap fraction of nffts for powerspectrum analysis.
    freq_tolerance: float
        frequency tollerance for combining fishes.
    rise_f_th: float
        minimum frequency difference between peak and base of a rise to be detected as such.
    prim_time_tolerance: float
        maximum time differencs in minutes in the first fish sorting step.
    max_time_tolerance: float
        maximum time difference in minutes between two fishes to combine these.
    f_th: float
        maximum frequency difference between two fishes to combine these.
    """
    cfg.add_section('Fish tracking:')
    cfg.add('DataSnippedSize', data_snipped_secs, 's', 'Duration of data snipped processed at once in seconds.')
    cfg.add('NfftPerPsd', nffts_per_psd, '', 'Number of nffts used for powerspectrum analysis.')
    cfg.add('FreqResolution', fresolution, 'Hz', 'Frequency resolution of the spectrogram')
    cfg.add('OverlapFrac', overlap_frac, '', 'Overlap fraction of the nffts during Powerspectrum analysis')
    cfg.add('FreqTolerance', freq_tolerance, 'Hz', 'Frequency tolernace in the first fish sorting step.')
    cfg.add('RiseFreqTh', rise_f_th, 'Hz', 'Frequency threshold for the primary rise detection.')
    cfg.add('PrimTimeTolerance', prim_time_tolerance, 'min', 'Time tolerance in the first fish sorting step.')
    cfg.add('MaxTimeTolerance', max_time_tolerance, 'min', 'Time tolerance between the occurrance of two fishes to join them.')
    cfg.add('FrequencyThreshold', f_th, 'Hz', 'Maximum Frequency difference between two fishes to join them.')


def tracker_args(cfg):
    """ Translates a configuration to the
    respective parameter names of the function fish_tracker().
    The return value can then be passed as key-word arguments to this function.

    Parameters
    ----------
    cfg: ConfigFile
        the configuration

    Returns (dict): dictionary with names of arguments of the clip_amplitudes() function and their values as supplied by cfg.
    -------
    dict
        dictionary with names of arguments of the fish_tracker() function and their values as supplied by cfg.
    """
    return cfg.map({'data_snipped_secs': 'DataSnippedSize',
                    'nffts_per_psd': 'NfftPerPsd',
                    'fresolution': 'FreqResolution',
                    'overlap_frac': 'OverlapFrac',
                    'freq_tolerance': 'FreqTolerance',
                    'rise_f_th': 'RiseFreqTh',
                    'prim_time_tolerance': 'PrimTimeTolerance',
                    'max_time_tolerance': 'MaxTimeTolerance',
                    'f_th': 'FrequencyThreshold'})


def fish_tracker(data_file, start_time=0.0, end_time=-1.0, gridfile=False, save_plot=False,
                 save_original_fishes=False, data_snippet_secs = 60., nffts_per_psd = 4, fresolution = 0.5,
                 overlap_frac =.9, freq_tolerance = 0.5, rise_f_th= .5, max_time_tolerance = 10.,
                 f_th= 5., output_folder = '.', plot_harmonic_groups=False, verbose=0, **kwargs):

    """
    Performs the steps to analyse long-term recordings of wave-type weakly electric fish including frequency analysis,
    fish tracking and more.

    In small data snippets spectrograms and power-spectra are calculated. With the help of the power-spectra harmonic
    groups and therefore electric fish fundamental frequencies can be detected. These fundamental frequencies are
    detected for every time-step throughout the whole file. Afterwards the fundamental frequencies get assigned to
    different fishes.

    :param data_file: (string) filepath of the analysed data file.
    :param data_snippet_secs: (float) duration of data snipped processed at once in seconds. Necessary because of memory issues.
    :param nffts_per_psd: (int) amount of nffts used to calculate one psd.
    :param start_time: (int) analyze data from this time on (in seconds).  XXX this should be a float!!!!
    :param end_time: (int) stop analysis at this time (in seconds).  XXX this should be a float!!!!
    :param plot_data_func: (function) if plot_data_func = plot_fishes creates a plot of the sorted fishes.
    :param save_original_fishes: (boolean) if True saves the sorted fishes after the first level of fish sorting.
    :param kwargs: further arguments are passed on to harmonic_groups().
    """
    if gridfile:
        data = open_data(data_file, -1, 60.0, 10.0)
        print('\n--- GRID FILE ANALYSIS ---')
        print('ALL traces are analysed')
        print('--------------------------')
    else:
        data = open_data(data_file, 0, 60.0, 10.0)
        print('\n--- ONE TRACE ANALYSIS ---')
        print('ONLY 1 trace is analysed')
        print('--------------------------')

    # with open_data(data_file, 0, 60.0, 10.0) as data:
    samplerate = data.samplerate
    base_name = os.path.splitext(os.path.basename(data_file))[0]
    
    if verbose >= 1:
        print('\nextract fundamentals...')
        if verbose >= 2:
            print('> frequency resolution = %.2f Hz' % fresolution)
            print('> nfft overlap fraction = %.2f' % overlap_frac)
    all_fundamentals, all_times = extract_fundamentals(data, samplerate, start_time, end_time,
                                                       data_snippet_secs, nffts_per_psd,
                                                       fresolution=fresolution,
                                                       overlap_frac=overlap_frac,
                                                       plot_harmonic_groups=plot_harmonic_groups,
                                                       verbose=verbose, **kwargs)

    if verbose >= 1:
        print('\nsorting fishes...')
        if verbose >= 2:
            print('> frequency tolerance = %.2f Hz' % freq_tolerance)
    fishes = first_level_fish_sorting(all_fundamentals, base_name, all_times, freq_tolerance=freq_tolerance,
                                      save_original_fishes=save_original_fishes, output_folder=output_folder, verbose=verbose)

    min_occure_time = all_times[-1] * 0.01 / 60.
    if min_occure_time > 1.:
        min_occure_time = 1.

    if verbose >= 1:
        print('\nexclude fishes...')
        if verbose >= 2:
            print('> minimum occur time: %.2f min' % min_occure_time)
    fishes = exclude_fishes(fishes, all_times, min_occure_time)

    if len(fishes) == 0:
        print('excluded all fishes. Change parameters.')
        quit()
    if verbose >= 1:
        print('\nrise detection...')
        if verbose >= 2:
            print('> rise frequency th = %.2f Hz' % rise_f_th)
    all_rises = detect_rises(fishes, all_times, rise_f_th, verbose=verbose)

    if verbose >= 1:
        print('\ncut fishes at rises...')
    fishes, all_rises = cut_at_rises(fishes, all_rises)

    if verbose >= 1:
        print('\ncombining fishes...')
        if verbose >= 2:
            print('> maximum time difference: %.2f min' % max_time_tolerance)
            print('> maximum frequency difference: %.2f Hz' % f_th)
    fishes, all_rises = combine_fishes(fishes, all_times, all_rises, max_time_tolerance, f_th)

    if verbose >= 1:
        print('%.0f fishes left' % len(fishes))

    if 'plt' in locals() or 'plt' in globals():
        plot_fishes(fishes, all_times, all_rises, base_name, save_plot, output_folder)

    if save_original_fishes:
        if verbose >= 1:
            print('saving data to ' + output_folder)
        save_data(fishes, all_times, all_rises, base_name, output_folder)
    if verbose >= 1:
        print('\nWhole file processed.')


def main():
    # config file name:
    cfgfile = __package__ + '.cfg'

    # command line arguments:
    parser = argparse.ArgumentParser(
        description='Analyse long single- or multi electrode EOD recordings of weakly electric fish.',
        epilog='by bendalab (2015-2017)')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('-v', action='count', dest='verbose', help='verbosity level')
    parser.add_argument('-c', '--save-config', nargs='?', default='', const=cfgfile,
                        type=str, metavar='cfgfile',
                        help='save configuration to file cfgfile (defaults to {0})'.format(cfgfile))
    parser.add_argument('file', nargs='?', default='', type=str, help='name of the file wih the time series data or the -fishes.npy file saved with the -s option')
    parser.add_argument('start_time', nargs='?', default=0.0, type=float, help='start time of analysis in min.')
    parser.add_argument('end_time', nargs='?', default=-1.0, type=float, help='end time of analysis in min.')
    parser.add_argument('-g', dest='grid', action='store_true', help='sum up spectrograms of all channels available.')
    parser.add_argument('-p', dest='save_plot', action='store_true', help='save output plot as png file')
    parser.add_argument('-s', dest='save_fish', action='store_true',
                        help='save fish EODs after first stage of sorting.')
    parser.add_argument('-f', dest='plot_harmonic_groups', action='store_true', help='plot harmonic group detection')
    parser.add_argument('-o', dest='output_folder', default=".", type=str,
                        help="path where to store results and figures")
    args = parser.parse_args()
    datafile = args.file

    # set verbosity level from command line:
    verbose = 0
    if args.verbose != None:
        verbose = args.verbose

    # configuration options:
    cfg = ConfigFile()
    add_psd_peak_detection_config(cfg)
    add_harmonic_groups_config(cfg)
    add_tracker_config(cfg)
    
    # load configuration from working directory and data directories:
    cfg.load_files(cfgfile, datafile, 3, verbose)

    # save configuration:
    if len(args.save_config) > 0:
        ext = os.path.splitext(args.save_config)[1]
        if ext != os.extsep + 'cfg':
            print('configuration file name must have .cfg as extension!')
        else:
            print('write configuration to %s ...' % args.save_config)
            cfg.dump(args.save_config)
        return

    # check data file:
    if len(datafile) == 0:
        parser.error('you need to specify a file containing some data')
        return

    # output directory:    
    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)

    if os.path.splitext(datafile)[1] == '.npy':
        rise_f_th = .5
        max_time_tolerance = 10.
        f_th = 5.
        output_folder = args.output_folder

        a = np.load(sys.argv[1], mmap_mode='r+')
        fishes = a.copy()

        all_times = np.load(sys.argv[1].replace('-fishes', '-times'))

        min_occure_time = all_times[-1] * 0.01 / 60.
        if min_occure_time > 1.:
            min_occure_time = 1.

        if verbose >= 1:
            print('\nexclude fishes...')
            if verbose >= 2:
                print('> minimum occur time: %.2f min' % min_occure_time)
        fishes = exclude_fishes(fishes, all_times, min_occure_time=min_occure_time)

        if verbose >= 1:
            print('\nrise detection...')
            if verbose >= 2:
                print('> rise frequency th = %.2f Hz' % rise_f_th)
        all_rises = detect_rises(fishes, all_times, rise_f_th, verbose)

        if verbose >= 1:
            print('\ncut fishes at rises...')
        fishes, all_rises = cut_at_rises(fishes, all_rises)

        if verbose >= 1:
            print('\ncombining fishes...')
            if verbose >= 2:
                print('> maximum time difference: %.2f min' % max_time_tolerance)
                print('> maximum frequency difference: %.2f Hz' % f_th)
        fishes, all_rises = combine_fishes(fishes, all_times, all_rises, max_time_tolerance, f_th)
        if verbose >= 1:
            print('%.0f fishes left' % len(fishes))

        base_name = os.path.splitext(os.path.basename(sys.argv[1]))[0]

        if 'plt' in locals() or 'plt' in globals():
            plot_fishes(fishes, all_times, all_rises, base_name, args.save_plot, args.output_folder)

        if args.save_fish:
            if verbose >= 1:
                print('saving data to ' + output_folder)
            save_data(fishes, all_times, all_rises, base_name, output_folder)

        if verbose >= 1:
            print('Whole file processed.')

    else:
        t_kwargs = psd_peak_detection_args(cfg)
        t_kwargs.update(harmonic_groups_args(cfg))
        t_kwargs.update(tracker_args(cfg))
        fish_tracker(datafile, args.start_time*60.0, args.end_time*60.0,
                     args.grid, args.save_plot, args.save_fish, output_folder=args.output_folder,
                     plot_harmonic_groups=args.plot_harmonic_groups, verbose=verbose, **t_kwargs)

if __name__ == '__main__':
    main()

