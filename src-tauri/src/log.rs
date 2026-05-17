use std::io::Write;

pub fn log_debug(msg: &str) {
    let log_path = std::env::temp_dir().join("airtype_debug.log");
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
    {
        let _ = writeln!(
            f,
            "[{}] {}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            msg
        );
    }
}
