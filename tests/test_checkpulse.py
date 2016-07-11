from nose.tools import assert_true, assert_equal, assert_almost_equal
import thunderfish.checkpulse as chp
import thunderfish.fakefish as ff
import thunderfish.powerspectrum as ps


def test_wavefish():

    # Get generated data from fakefish
    rec_len = 10.
    samplerate = 44100.
    fake_lepto = ff.generate_alepto(750., samplerate, rec_len, noise_std=0.03)

    # Test checkpulse based on the width of detected peaks:
    fishtype_pw = chp.check_pulse_width(fake_lepto, samplerate)[0]  # pw stands for peak_width
    # fishtype should be False, because apteronotus signal is wave-type
    print('peak_width test gives boolean : ' + str(fishtype_pw))
    assert_true(~fishtype_pw, 'checkpulse.check_pulse_width() is not detecting Aperonotus signal as wave-type')

    # Test checkpulse based on its signature on the power spectrum
    psd_data = ps.multi_resolution_psd(fake_lepto, samplerate)
    fishtype_psd = chp.check_pulse_psd(psd_data[0], psd_data[1])[0]
    # fishtype should be False, because apteronotus signal is wave-type
    print('\npsd test gives boolean : ' + str(fishtype_psd))
    quit()
    assert_true(~fishtype_psd, 'checkpulse.check_pulse_psd() is not detecting Aperonotus signal as wave-type')

    pass


def test_pulsefish():

    pass

if __name__ == '__main__':
    test_wavefish()