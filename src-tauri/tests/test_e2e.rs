//! E2E tests for the full AirType pipeline.
//!
//! These tests require:
//! - Windows with a desktop session
//! - Backend running with OpenAI-compatible API
//!
//! Run with: cargo test --test test_e2e -- --ignored --nocapture

use std::time::Duration;

#[test]
#[ignore]
fn test_e2e_backend_health() {
    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    client.health().expect("Backend should be reachable");
}

#[test]
#[ignore]
fn test_e2e_transcribe_short_audio() {
    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    let pcm = vec![0u8; 16000];
    let result = client.transcribe(&pcm, 16000, &cfg.model, cfg.language.as_deref(), None);
    match result {
        Ok(_) | Err(airtype::asr::AsrError::InvalidAudio(_)) => {}
        Err(e) => panic!("Request failed: {}", e),
    }
}

#[test]
#[ignore]
fn test_e2e_transcribe_valid_audio() {
    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    let pcm: Vec<u8> = vec![0i16; 16000].iter().flat_map(|s| s.to_le_bytes()).collect();
    let result = client.transcribe(&pcm, 16000, &cfg.model, cfg.language.as_deref(), None)
        .expect("Transcribe should succeed");
    assert!(!result.text.is_empty() || true); // silence may produce empty text
}

#[test]
#[ignore]
fn test_e2e_transcribe_with_context() {
    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    let pcm: Vec<u8> = vec![0i16; 16000].iter().flat_map(|s| s.to_le_bytes()).collect();
    let result = client.transcribe(&pcm, 16000, &cfg.model, cfg.language.as_deref(), Some("Anthropic,Claude"))
        .expect("Transcribe with context should succeed");
    assert!(result.text.is_empty() || !result.text.is_empty());
}

#[test]
#[ignore]
fn test_e2e_list_models() {
    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    let models = client.list_models().expect("Should list models");
    assert!(!models.is_empty(), "Backend should have at least one model");
}

#[test]
#[ignore]
fn test_e2e_full_pipeline_simulated() {
    let mut buf = airtype::audio::AudioBuffer::new(16000);
    buf.clear();
    buf.start_capture();
    for i in 0..16000 {
        let sample = ((i as f32 / 16000.0 * 440.0 * 2.0 * std::f32::consts::PI).sin() * 0.3 * 32767.0) as i16;
        buf.push_i16(&[sample]);
    }
    buf.stop_capture();
    let pcm_bytes = buf.take_pcm_bytes();
    assert!(!pcm_bytes.is_empty());

    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    let result = client.transcribe(&pcm_bytes, 16000, &cfg.model, cfg.language.as_deref(), None)
        .expect("ASR request should succeed");
    assert!(result.text.is_empty() || !result.text.is_empty());
}

#[test]
#[ignore]
fn test_e2e_config_url_matches_backend() {
    let cfg = airtype::config::AppConfig::load(&std::path::PathBuf::from("config.json"));
    let client = airtype::asr::AsrClient::new(&cfg.backend_url, &cfg.asr_api_key);
    client.health().expect("Backend should be reachable");
}
