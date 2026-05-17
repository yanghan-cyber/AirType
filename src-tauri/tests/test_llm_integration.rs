use airtype::config::{AppConfig, ProcessingMode};
use airtype::llm::{LlmClient, LlmConfig};

#[test]
fn test_processing_mode_template_with_timestamp() {
    let mode = ProcessingMode {
        id: "test".to_string(),
        name: "Test".to_string(),
        icon: "🧪".to_string(),
        system_prompt: String::new(),
        user_template: "时间：{timestamp}，内容：{asr_text}".to_string(),
        show_in_popup: false,
        popup_order: 0,
    };

    let result = mode.apply_template("你好世界");
    assert!(result.contains("你好世界"));
    assert!(result.contains("时间："));
    assert!(result.contains("内容："));
}

#[test]
fn test_config_with_llm_settings() {
    let mut cfg = AppConfig::default();
    cfg.llm.base_url = "http://localhost:11434/v1".to_string();
    cfg.llm.api_key = "test-key".to_string();
    cfg.llm.model = "llama3".to_string();
    cfg.default_processing_mode = "polish".to_string();

    assert_eq!(cfg.llm.base_url, "http://localhost:11434/v1");
    assert_eq!(cfg.llm.api_key, "test-key");
    assert_eq!(cfg.llm.model, "llama3");
    assert_eq!(cfg.default_processing_mode, "polish");
}

#[test]
fn test_config_json_roundtrip_with_llm() {
    let mut cfg = AppConfig::default();
    cfg.llm.api_key = "secret-key".to_string();
    cfg.llm.model = "gpt-4".to_string();
    cfg.default_processing_mode = "translate_en".to_string();
    cfg.hotkey_secondary = Some("Ctrl+Alt".to_string());

    let json = serde_json::to_string(&cfg).unwrap();
    let loaded: AppConfig = serde_json::from_str(&json).unwrap();

    assert_eq!(loaded.llm.api_key, "secret-key");
    assert_eq!(loaded.llm.model, "gpt-4");
    assert_eq!(loaded.default_processing_mode, "translate_en");
    assert_eq!(loaded.hotkey_secondary, Some("Ctrl+Alt".to_string()));
}

#[test]
fn test_llm_client_creation_with_custom_config() {
    let config = LlmConfig {
        base_url: "http://localhost:11434/v1".to_string(),
        api_key: "test".to_string(),
        model: "llama3".to_string(),
        temperature: 0.5,
        max_tokens: 1024,
        extra_params: None,
    };
    let client = LlmClient::new(config);
    assert_eq!(client.config.base_url, "http://localhost:11434/v1");
    assert_eq!(client.config.model, "llama3");
}

#[test]
fn test_default_processing_modes_exist() {
    let cfg = AppConfig::default();
    let ids: Vec<&str> = cfg.processing_modes.iter().map(|m| m.id.as_str()).collect();
    assert!(ids.contains(&"direct"));
    assert!(ids.contains(&"polish"));
    assert!(ids.contains(&"translate_en"));
}

#[test]
fn test_partial_config_json_backward_compat() {
    // Simulate old config without LLM fields
    let json = r#"{"hotkey":"Ctrl+Win","enabled":true}"#;
    let cfg: AppConfig = serde_json::from_str(json).unwrap();
    assert_eq!(cfg.hotkey, "Ctrl+Win");
    assert_eq!(cfg.llm.model, "gpt-4o-mini"); // default
    assert_eq!(cfg.default_processing_mode, "direct"); // default
    assert!(!cfg.processing_modes.is_empty()); // defaults
}
