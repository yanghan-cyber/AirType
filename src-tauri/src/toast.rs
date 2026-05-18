use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};
use crate::log::log_debug;

pub fn show_toast(app: &AppHandle, message: &str) {
    // Skip if toast already exists
    if app.get_webview_window("toast").is_some() {
        return;
    }

    let url = format!("toast.html#{}", urlencoding(message));
    let builder = WebviewWindowBuilder::new(
        app,
        "toast",
        WebviewUrl::App(url.into()),
    )
    .title("AirType Toast")
    .inner_size(180.0, 40.0)
    .decorations(false)
    .transparent(true)
    .shadow(false)
    .always_on_top(true)
    .skip_taskbar(true)
    .resizable(false)
    .focusable(false)
    .visible(false);

    match builder.build() {
        Ok(win) => {
            position_toast(&win, app);
            let _ = win.show();
            log_debug("[toast] Window created");
        }
        Err(e) => {
            log_debug(&format!("[toast] Failed to create window: {}", e));
        }
    }
}

fn position_toast(win: &tauri::WebviewWindow, app: &AppHandle) {
    let toast_w = 180.0;
    let toast_h = 40.0;

    if let Some(monitor) = app.primary_monitor().ok().flatten() {
        let size = monitor.size();
        let scale = monitor.scale_factor();
        let screen_w = size.width as f64;

        // Use Windows work area bottom (excludes taskbar) for accurate positioning
        let work_bottom = get_work_area_bottom()
            .unwrap_or_else(|| size.height as i32 - 48) as f64;

        let x = (screen_w - toast_w * scale - 16.0 * scale) as i32;
        let y = (work_bottom - toast_h * scale - 8.0 * scale) as i32;

        let _ = win.set_position(tauri::Position::Physical(
            tauri::PhysicalPosition::new(x, y)
        ));
    }
}

#[cfg(target_os = "windows")]
fn get_work_area_bottom() -> Option<i32> {
    use windows::Win32::Foundation::RECT;
    use windows::Win32::UI::WindowsAndMessaging::{SystemParametersInfoW, SPI_GETWORKAREA};

    let mut rect = RECT::default();
    let result = unsafe {
        SystemParametersInfoW(
            SPI_GETWORKAREA,
            0,
            Some(&mut rect as *mut _ as *mut _),
            Default::default(),
        )
    };
    if result.is_ok() { Some(rect.bottom) } else { None }
}

#[cfg(not(target_os = "windows"))]
fn get_work_area_bottom() -> Option<i32> { None }

fn urlencoding(s: &str) -> String {
    s.bytes().map(|b| {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => (b as char).to_string(),
            _ => format!("%{:02X}", b),
        }
    }).collect()
}

#[tauri::command]
pub fn close_toast_window(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("toast") {
        let _ = win.close();
    }
}
