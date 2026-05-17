#[test]
fn test_audio_buffer_capture_cycle() {
    let mut buf = airtype::audio::AudioBuffer::new(16000);
    buf.start_capture();
    let samples: Vec<i16> = (0..16000).map(|i| (i % 256) as i16).collect();
    buf.push_i16(&samples);
    assert!(buf.duration_secs() >= 0.99);
    buf.stop_capture();
    let pcm = buf.take_pcm_bytes();
    assert_eq!(pcm.len(), 32000);
}

#[test]
fn test_audio_resample_preserves_amplitude() {
    let samples: Vec<f32> = (0..48000)
        .map(|i| (i as f32 / 48000.0 * 440.0 * 2.0 * std::f32::consts::PI).sin() * 0.5)
        .collect();
    let resampled = airtype::audio::resample(&samples, 48000, 16000);
    assert_eq!(resampled.len(), 16000);
    let max_val = resampled.iter().cloned().fold(0.0f32, f32::max);
    assert!(max_val > 0.3, "Resampled audio should preserve amplitude");
}

#[test]
fn test_rms_with_resampled_data() {
    let samples: Vec<i16> = (0..16000)
        .map(|i| ((i as f32 / 16000.0 * 440.0 * 2.0 * std::f32::consts::PI).sin() * 0.5 * 32767.0) as i16)
        .collect();
    let rms = airtype::audio::calculate_rms(&samples);
    assert!(rms > 0.2, "RMS should be non-zero for sine wave");
    assert!(rms < 0.5, "RMS of half-amplitude sine should be < 0.5");
}

#[test]
fn test_bar_heights_converge() {
    let mut smooth = [0.0; 5];
    let weights = [0.5, 0.8, 1.0, 0.75, 0.55];
    for _ in 0..20 {
        let _ = airtype::audio::compute_bar_heights(0.6, &weights, &mut smooth);
    }
    let bars = airtype::audio::compute_bar_heights(0.6, &weights, &mut smooth);
    assert!(bars[2] > 0.3, "Center bar should converge above 0.3");
}
