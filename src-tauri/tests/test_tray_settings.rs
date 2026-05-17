use tempfile::TempDir;

#[test]
fn test_config_round_trip_through_save() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("config.json");

    let cfg = airtype::config::AppConfig {
        hotkey: "Ctrl+Alt+A".into(),
        enabled: false,
        model: "Qwen3-ASR-1.7B".into(),
        hotwords: vec!["测试".into(), "hello".into()],
        language: Some("zh".into()),
        backend_url: "http://localhost:9999".into(),
        capsule_x: Some(100),
        capsule_y: Some(200),
        capsule_default_position: "top".into(),
        capsule_default_offset: 50,
        ..Default::default()
    };
    cfg.save(&path);

    let loaded = airtype::config::AppConfig::load(&path);
    assert_eq!(loaded.hotkey, "Ctrl+Alt+A");
    assert!(!loaded.enabled);
    assert_eq!(loaded.model, "Qwen3-ASR-1.7B");
    assert_eq!(loaded.hotwords, vec!["测试", "hello"]);
    assert_eq!(loaded.language, Some("zh".into()));
    assert_eq!(loaded.backend_url, "http://localhost:9999");
    assert_eq!(loaded.capsule_x, Some(100));
    assert_eq!(loaded.capsule_y, Some(200));
}

#[test]
fn test_config_default_values() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("nonexistent.json");

    let cfg = airtype::config::AppConfig::load(&path);
    assert_eq!(cfg.hotkey, "Ctrl+Win");
    assert!(cfg.enabled);
    assert_eq!(cfg.model, "Qwen3-ASR-0.6B");
    assert!(cfg.hotwords.is_empty());
    assert!(cfg.language.is_none());
    assert_eq!(cfg.backend_url, "https://api.openai.com/v1");
}

#[test]
fn test_config_hotword_context_string() {
    let cfg = airtype::config::AppConfig {
        hotwords: vec!["A".into(), "B".into(), "C".into()],
        ..Default::default()
    };
    assert_eq!(cfg.context_string(), "A,B,C");

    let empty = airtype::config::AppConfig::default();
    assert_eq!(empty.context_string(), "");

    let single = airtype::config::AppConfig {
        hotwords: vec!["单热词".into()],
        ..Default::default()
    };
    assert_eq!(single.context_string(), "单热词");
}

#[test]
fn test_config_model_path_variants() {
    let cfg06 = airtype::config::AppConfig {
        model: "Qwen3-ASR-0.6B".into(),
        ..Default::default()
    };
    assert_eq!(cfg06.model_path(), "models/Qwen3-ASR-0.6B");

    let cfg17 = airtype::config::AppConfig {
        model: "Qwen3-ASR-1.7B".into(),
        ..Default::default()
    };
    assert_eq!(cfg17.model_path(), "models/Qwen3-ASR-1.7B");
}

#[test]
fn test_config_save_creates_file() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("new_config.json");
    assert!(!path.exists());

    let cfg = airtype::config::AppConfig::default();
    cfg.save(&path);
    assert!(path.exists());

    let content = std::fs::read_to_string(&path).unwrap();
    let parsed: serde_json::Value = serde_json::from_str(&content).unwrap();
    assert_eq!(parsed["hotkey"], "Ctrl+Win");
    assert_eq!(parsed["backend_url"], "https://api.openai.com/v1");
}

#[test]
fn test_config_save_and_reload_preserves_all_fields() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("config.json");

    let original = airtype::config::AppConfig {
        hotkey: "Alt+Shift+S".into(),
        enabled: true,
        model: "Qwen3-ASR-0.6B".into(),
        hotwords: vec!["你好".into(), "世界".into()],
        language: Some("en".into()),
        backend_url: "http://192.168.1.100:8080".into(),
        capsule_x: Some(500),
        capsule_y: Some(600),
        capsule_default_position: "bottom".into(),
        capsule_default_offset: 100,
        ..Default::default()
    };
    original.save(&path);

    let reloaded = airtype::config::AppConfig::load(&path);
    assert_eq!(reloaded.hotkey, original.hotkey);
    assert_eq!(reloaded.enabled, original.enabled);
    assert_eq!(reloaded.model, original.model);
    assert_eq!(reloaded.hotwords, original.hotwords);
    assert_eq!(reloaded.language, original.language);
    assert_eq!(reloaded.backend_url, original.backend_url);
    assert_eq!(reloaded.capsule_x, original.capsule_x);
    assert_eq!(reloaded.capsule_y, original.capsule_y);
}
