from nose.tools import assert_true, assert_equal, assert_almost_equal
import thunderfish.checkpulse as chp
import thunderfish.fakefish as ff
import thunderfish.powerspectrum as ps


def test_wavefish():

    # Get wavefish data from fakefish
    rec_len = 10.
    freq = 750.
    samplerate = 44100.
    fake_lepto = ff.generate_alepto(freq, samplerate, rec_len, noise_std=0.03, jitter_percentile=0.03)

    # Test checkpulse based on the width of detected peaks:
    fishtype_pw = chp.check_pulse_width(fake_lepto, samplerate)[0]  # pw stands for peak_width
    # fishtype should be False, because apteronotus signal is wave-type
    print('peak_width test for wave-signal gives boolean : ' + str(fishtype_pw))
    assert_true(~fishtype_pw, 'checkpulse.check_pulse_width() is not detecting Aperonotus signal as wave-type')

    # Test checkpulse based on its signature on the power spectrum
    psd_data = ps.multi_resolution_psd(fake_lepto, samplerate)
    fishtype_psd = chp.check_pulse_psd(psd_data[0], psd_data[1])[0]
    # fishtype should be False, because apteronotus signal is wave-type
    print('\npsd test for wave-signal gives boolean : ' + str(fishtype_psd))
    assert_true(~fishtype_psd, 'checkpulse.check_pulse_psd() is not detecting Aperonotus signal as wave-type')

    pass


def test_pulsefish():

    # Get pulsefish data from fakefish
    rec_len = 10.
    freq = 85.
    samplerate = 44100.
    fake_pulse = ff.generate_triphasic_pulses(freq, samplerate, rec_len, noise_std=0.02, jitter_cv=0.03)

    # Test checkpulse based on the width of detected peaks:
    fishtype_pw = chp.check_pulse_width(fake_pulse, samplerate)[0]  # pw stands for peak_width
    # fishtype should be True, because signal is pulse-fish like
    print('peak_width test for pulse-signal gives boolean : ' + str(fishtype_pw))
    assert_true(fishtype_pw, 'checkpulse.check_pulse_width() is not detecting triphasic pulse-fish as pulse-type')

    # Test checkpulse based on its signature on the power spectrum
    psd_data = ps.multi_resolution_psd(fake_pulse, samplerate)
    fishtype_psd = chp.check_pulse_psd(psd_data[0], psd_data[1])[0]
    # fishtype should be True, because signal is pulse-fish like
    print('\npsd test for pulse-signal gives boolean : ' + str(fishtype_psd))
    assert_true(fishtype_psd, 'checkpulse.check_pulse_psd() is not detecting triphasic pulse-fish as pulse-type')

    pass

if __name__ == '__main__':
    test_wavefish()
    test_pulsefish()