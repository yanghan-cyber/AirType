fn start_mock_server() -> mockito::ServerGuard {
    mockito::Server::new()
}

#[test]
fn test_health_connected() {
    let mut server = start_mock_server();
    let mock = server.mock("GET", "/models")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{"data":[{"id":"whisper-large-v3"}]}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    assert!(client.health().is_ok());
    mock.assert();
}

#[test]
fn test_health_any_response_ok() {
    let mut server = start_mock_server();
    let mock = server.mock("GET", "/models")
        .with_status(404)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    assert!(client.health().is_ok());
    mock.assert();
}

#[test]
fn test_health_connection_failed() {
    let client = airtype::asr::AsrClient::new("http://127.0.0.1:1", "");
    assert!(client.health().is_err());
}

#[test]
fn test_transcribe_success() {
    let mut server = start_mock_server();
    let mock = server.mock("POST", "/audio/transcriptions")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{"text":"你好世界"}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    let pcm = vec![0u8; 32000];
    let result = client.transcribe(&pcm, 16000, "whisper-large-v3", None, None).unwrap();
    assert_eq!(result.text, "你好世界");
    mock.assert();
}

#[test]
fn test_transcribe_with_prompt_and_language() {
    let mut server = start_mock_server();
    let mock = server.mock("POST", "/audio/transcriptions")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{"text":"魔搭社区的Claude"}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    let pcm = vec![0u8; 32000];
    let result = client.transcribe(&pcm, 16000, "whisper-large-v3", Some("zh"), Some("魔搭社区,Claude")).unwrap();
    assert_eq!(result.text, "魔搭社区的Claude");
    mock.assert();
}

#[test]
fn test_transcribe_model_not_loaded_503() {
    let mut server = start_mock_server();
    let mock = server.mock("POST", "/audio/transcriptions")
        .with_status(503)
        .with_header("content-type", "application/json")
        .with_body(r#"{"error":"Model not loaded"}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    let pcm = vec![0u8; 32000];
    let err = client.transcribe(&pcm, 16000, "whisper-large-v3", None, None).unwrap_err();
    assert!(matches!(err, airtype::asr::AsrError::ModelNotLoaded));
    mock.assert();
}

#[test]
fn test_transcribe_bad_audio_400() {
    let mut server = start_mock_server();
    let mock = server.mock("POST", "/audio/transcriptions")
        .with_status(400)
        .with_header("content-type", "application/json")
        .with_body(r#"{"error":"Audio too short"}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    let pcm = vec![0u8; 100];
    let err = client.transcribe(&pcm, 16000, "whisper-large-v3", None, None).unwrap_err();
    assert!(matches!(err, airtype::asr::AsrError::InvalidAudio(_)));
    mock.assert();
}

#[test]
fn test_transcribe_with_api_key() {
    let mut server = start_mock_server();
    let mock = server.mock("POST", "/audio/transcriptions")
        .match_header("Authorization", "Bearer test-key")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{"text":"hello"}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "test-key");
    let pcm = vec![0u8; 32000];
    let result = client.transcribe(&pcm, 16000, "whisper-large-v3", None, None).unwrap();
    assert_eq!(result.text, "hello");
    mock.assert();
}

#[test]
fn test_list_models() {
    let mut server = start_mock_server();
    let mock = server.mock("GET", "/models")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{"data":[{"id":"whisper-large-v3"},{"id":"whisper-small"}]}"#)
        .create();
    let client = airtype::asr::AsrClient::new(&server.url(), "");
    let models = client.list_models().unwrap();
    assert_eq!(models, vec!["whisper-small", "whisper-large-v3"]);
    mock.assert();
}
