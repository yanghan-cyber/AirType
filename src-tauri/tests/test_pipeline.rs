use std::sync::{Arc, Mutex};

#[test]
fn test_full_pipeline_state_transitions() {
    let mut state = airtype::state::RecordingState::Idle;
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Recording { started_at: std::time::Instant::now() }).unwrap();
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Processing).unwrap();
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Done).unwrap();
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Idle).unwrap();
}

#[test]
fn test_pipeline_error_flow() {
    let mut state = airtype::state::RecordingState::Idle;
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Recording { started_at: std::time::Instant::now() }).unwrap();
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Processing).unwrap();
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Error("backend timeout".into())).unwrap();
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Idle).unwrap();
}

#[test]
fn test_pipeline_cancel_recording() {
    let mut state = airtype::state::RecordingState::Idle;
    airtype::state::transition_to(&mut state, airtype::state::RecordingState::Recording { started_at: std::time::Instant::now() }).unwrap();
    let result = airtype::state::transition_to(&mut state, airtype::state::RecordingState::Idle);
    assert!(result.is_ok());
}

#[test]
fn test_audio_buffer_pipeline_cycle() {
    let mut buf = airtype::audio::AudioBuffer::new(16000);
    buf.start_capture();
    for i in 0..1600 {
        buf.push_i16(&[(i as f32 * 0.01).sin() as i16]);
    }
    buf.stop_capture();
    let pcm = buf.take_pcm_bytes();
    assert!(!pcm.is_empty());
    assert_eq!(pcm.len() % 2, 0);
    let pcm2 = buf.take_pcm_bytes();
    assert!(pcm2.is_empty());
}

#[test]
fn test_config_context_string_with_hotwords() {
    let cfg = airtype::config::AppConfig {
        hotwords: vec!["Anthropic".into(), "Claude".into()],
        ..Default::default()
    };
    assert_eq!(cfg.context_string(), "Anthropic,Claude");
}

#[test]
fn test_config_context_string_empty() {
    let cfg = airtype::config::AppConfig::default();
    assert_eq!(cfg.context_string(), "");
}

#[test]
fn test_config_model_path_mapping() {
    let cfg = airtype::config::AppConfig {
        model: "Qwen3-ASR-0.6B".into(),
        ..Default::default()
    };
    assert_eq!(cfg.model_path(), "models/Qwen3-ASR-0.6B");
}
