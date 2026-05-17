use std::fs;
use tempfile::TempDir;

fn load_config_from_file(path: &std::path::PathBuf) -> serde_json::Value {
    let content = fs::read_to_string(path).unwrap();
    serde_json::from_str(&content).unwrap()
}

#[test]
fn test_config_file_has_all_fields() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("config.json");
    let cfg = airtype::config::AppConfig::default();
    cfg.save(&path);

    let json = load_config_from_file(&path);
    assert!(json.get("hotkey").is_some());
    assert!(json.get("enabled").is_some());
    assert!(json.get("model").is_some());
    assert!(json.get("hotwords").is_some());
    assert!(json.get("language").is_some());
    assert!(json.get("backend_url").is_some());
    assert!(json.get("max_recording_secs").is_some());
}

#[test]
fn test_config_partial_json_fills_defaults() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("config.json");
    fs::write(&path, r#"{"hotkey":"Alt+F12"}"#).unwrap();
    let cfg = airtype::config::AppConfig::load(&path);
    assert_eq!(cfg.hotkey, "Alt+F12");
    assert!(cfg.enabled);
    assert_eq!(cfg.model, "Qwen3-ASR-0.6B");
}

#[test]
fn test_config_overwrite_existing() {
    let dir = TempDir::new().unwrap();
    let path = dir.path().join("config.json");
    let mut cfg = airtype::config::AppConfig::default();
    cfg.backend_url = "http://localhost:9999".into();
    cfg.save(&path);

    let mut cfg2 = airtype::config::AppConfig::load(&path);
    assert_eq!(cfg2.backend_url, "http://localhost:9999");
    cfg2.backend_url = "http://localhost:8080".into();
    cfg2.save(&path);

    let cfg3 = airtype::config::AppConfig::load(&path);
    assert_eq!(cfg3.backend_url, "http://localhost:8080");
}
