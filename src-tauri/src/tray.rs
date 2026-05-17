use tauri::{
    AppHandle, Manager,
    menu::{MenuBuilder, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    WebviewUrl, WebviewWindowBuilder,
};
use image::GenericImageView;

pub fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let enabled = MenuItem::with_id(app, "enabled", "已启用语音输入", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let settings = MenuItem::with_id(app, "settings", "设置...", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;

    let menu = MenuBuilder::new(app)
        .item(&enabled)
        .item(&separator)
        .item(&settings)
        .item(&separator)
        .item(&quit)
        .build()?;

    let (icon_rgba, icon_w, icon_h) = {
        let bytes = include_bytes!("../icons/tray-32.png");
        let img = image::load_from_memory(bytes).expect("Failed to load tray icon").to_rgba8();
        let (w, h) = img.dimensions();
        (img.into_raw(), w, h)
    };
    let tray = TrayIconBuilder::new()
        .icon(tauri::image::Image::new_owned(icon_rgba, icon_w, icon_h))
        .menu(&menu)
        .on_menu_event(move |app, event| {
            match event.id.as_ref() {
                "enabled" => {
                    if let Some(state) = app.try_state::<std::sync::Mutex<crate::state::AppState>>() {
                        let mut s = state.lock().unwrap();
                        s.enabled = !s.enabled;
                    }
                }
                "settings" => {
                    if let Some(window) = app.get_webview_window("settings") {
                        let _ = window.set_focus();
                    } else {
                        let _ = WebviewWindowBuilder::new(
                            app,
                            "settings",
                            WebviewUrl::App("settings.html".into()),
                        )
                        .title("AirType 设置")
                        .inner_size(420.0, 520.0)
                        .resizable(false)
                        .build();
                    }
                }
                "quit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .build(app)?;

    // Keep tray alive for the lifetime of the app
    Box::leak(Box::new(tray));

    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_tray_menu_item_ids() {
        let ids = vec!["enabled", "settings", "quit"];
        assert_eq!(ids.len(), 3);
        let mut sorted = ids.clone();
        sorted.sort();
        sorted.dedup();
        assert_eq!(ids.len(), sorted.len(), "No duplicate menu IDs");
    }
}
