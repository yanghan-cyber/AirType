# Startup Toast Notification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a brief "AirType 已启动" toast notification near the system tray on app startup.

**Architecture:** New lightweight transparent Tauri window (`toast.html` + `toast.rs`) positioned at bottom-right of primary monitor. Created on startup with 500ms delay, auto-dismisses after 2.5s via JS animation. Reusable `show_toast(app, message)` API for future use.

**Tech Stack:** Tauri v2 (Rust + HTML/CSS/JS), Windows API

---

### Task 1: Create `ui/toast.html`

**Files:**
- Create: `ui/toast.html`

- [ ] **Step 1: Create the toast HTML file**

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  background: transparent;
  width: 100vw; height: 100vh;
  overflow: hidden;
  font-family: 'Segoe UI', -apple-system, sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
}
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #181818;
  border: 1px solid rgba(29,217,96,0.15);
  border-radius: 8px;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast.hide { opacity: 0; transform: translateY(-4px); }
.dot {
  width: 6px; height: 6px;
  background: #1ed760;
  border-radius: 50%;
  flex-shrink: 0;
}
.text {
  color: #fff; font-size: 12px;
  font-weight: 500; white-space: nowrap;
}
</style>
</head>
<body>
<div class="toast" id="toast">
  <div class="dot"></div>
  <span class="text" id="msg"></span>
</div>
<script>
const message = decodeURIComponent(location.hash.slice(1)) || 'AirType 已启动';
document.getElementById('msg').textContent = message;

document.addEventListener('DOMContentLoaded', async () => {
  const toast = document.getElementById('toast');

  // Fade in
  await new Promise(r => requestAnimationFrame(r));
  toast.classList.add('show');

  // Hold
  await new Promise(r => setTimeout(r, 2500));

  // Fade out
  toast.classList.remove('show');
  toast.classList.add('hide');
  await new Promise(r => setTimeout(r, 300));

  // Close window
  if (window.__TAURI__) {
    window.__TAURI__.core.invoke('close_toast_window');
  }
});
</script>
</body>
</html>
```

- [ ] **Step 2: Verify file is valid HTML**

Open `ui/toast.html` in a browser. Expected: a dark rounded rectangle appears with a green dot and "AirType 已启动" text, then fades out after 2.5s. The `window.__TAURI__` call will fail in a plain browser — that's expected.

---

### Task 2: Give tray icon an ID for future positioning

**Files:**
- Modify: `src-tauri/src/tray.rs:29`

- [ ] **Step 1: Change `TrayIconBuilder::new()` to `TrayIconBuilder::with_id("main")`**

In `src-tauri/src/tray.rs`, line 29, change:

```rust
// Before:
let tray = TrayIconBuilder::new()

// After:
let tray = TrayIconBuilder::with_id("main")
```

This lets us retrieve the tray via `app.tray_by_id("main")` for positioning.

---

### Task 3: Create `src-tauri/src/toast.rs`

**Files:**
- Create: `src-tauri/src/toast.rs`

- [ ] **Step 1: Create the toast module**

```rust
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
    .visible(true);

    match builder.build() {
        Ok(win) => {
            position_toast(&win, app);
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

    // Position at bottom-right of primary monitor (near system tray)
    if let Some(monitor) = app.primary_monitor().ok().flatten() {
        let size = monitor.size();
        let scale = monitor.scale_factor();
        let screen_w = size.width as f64;
        let screen_h = size.height as f64;

        // Use physical coordinates
        let x = screen_w - (toast_w * scale) as i32 - 16;
        let y = screen_h - (toast_h * scale) as i32 - 16;

        let _ = win.set_position(tauri::Position::Physical(
            tauri::PhysicalPosition::new(x, y)
        ));
    }
}

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
```

**Note:** The `urlencoding` function is a minimal percent-encoder. It handles UTF-8 bytes correctly for Chinese characters (each byte becomes `%XX`). The Tauri `WebviewUrl::App` path handles the hash fragment.

---

### Task 4: Wire up in `src-tauri/src/main.rs`

**Files:**
- Modify: `src-tauri/src/main.rs`

- [ ] **Step 1: Add `mod toast;` declaration**

After line 11 (`mod tray;`), add:

```rust
mod toast;
```

- [ ] **Step 2: Register `close_toast_window` command**

In the `invoke_handler` list (line 69), add `toast::close_toast_window` at the end:

```rust
            commands::cancel_llm_processing,
            toast::close_toast_window,
        ])
```

- [ ] **Step 3: Call `show_toast` after startup with 500ms delay**

After line 111 (`open_capsule_window(app.handle());`), add:

```rust
            // Show startup toast after a short delay (tray icon needs time to initialize)
            let toast_app = app.handle().clone();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_millis(500));
                toast::show_toast(&toast_app, "AirType 已启动");
            });
```

---

### Task 5: Build and test

- [ ] **Step 1: Build the project**

Run: `cd src-tauri && cargo build`
Expected: Compiles without errors.

- [ ] **Step 2: Run the app**

Run: `cd src-tauri && cargo run`
Expected:
1. App starts, tray icon appears
2. After ~500ms, a small dark toast appears near the bottom-right corner of the screen
3. Toast shows a green dot + "AirType 已启动" text
4. Toast fades in smoothly
5. After 2.5s, toast fades out smoothly
6. Toast window closes automatically
7. Capsule hotkey still works normally (no interference)

- [ ] **Step 3: Commit**

```bash
git add ui/toast.html src-tauri/src/toast.rs src-tauri/src/tray.rs src-tauri/src/main.rs
git commit -m "feat: add startup toast notification near system tray"
```
