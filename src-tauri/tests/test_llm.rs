use airtype::llm::*;

#[test]
fn test_llm_config_default() {
    let config = LlmConfig::default();
    assert_eq!(config.base_url, "https://api.openai.com/v1");
    assert_eq!(config.model, "gpt-4o-mini");
    assert_eq!(config.temperature, 0.7);
    assert_eq!(config.max_tokens, 2048);
}

#[test]
fn test_llm_error_display() {
    assert!(LlmError::ConnectionFailed("refused".into()).to_string().contains("refused"));
    assert!(LlmError::AuthenticationFailed.to_string().contains("认证"));
    assert!(LlmError::ModelNotFound("gpt-5".into()).to_string().contains("gpt-5"));
    assert!(LlmError::RequestTimeout.to_string().contains("超时"));
    assert!(LlmError::ApiError(400, "bad".into()).to_string().contains("400"));
}

#[test]
fn test_llm_client_new() {
    let config = LlmConfig::default();
    let client = LlmClient::new(config);
    assert_eq!(client.config.model, "gpt-4o-mini");
}
