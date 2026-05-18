# Startup Toast Notification

## Summary

Add a lightweight Toast notification window near the system tray icon that briefly shows "AirType 已启动" on app launch, so users know the app has started successfully.

## Context

AirType runs in the background with only a system tray icon. When the app starts, there is no visible feedback — users may not realize it's running. A brief Toast notification near the tray solves this.

## Requirements

- Toast appears near system tray icon on app startup
- Shows "AirType 已启动" with a green dot, matching existing design language
- Auto-dismisses after ~2.5 seconds (fade-out animation)
- No user interaction required
- Must not interfere with capsule window or normal operation

## Design

### Files

| File | Action | Purpose |
|------|--------|---------|
| `ui/toast.html` | New | Minimal Toast UI page |
| `src-tauri/src/toast.rs` | New | Toast window creation, positioning, lifecycle |
| `src-tauri/src/main.rs` | Modify | Call toast after startup |

### Toast Window Appearance

- Size: ~180x40px
- Background: `#181818` (matches capsule)
- Border-radius: 8px
- Subtle green accent border: `1px solid rgba(29,217,96,0.15)`
- Content: green dot (6px, `#1ed760`) + "AirType 已启动" (12px, white, Segoe UI)
- Window properties: `always_on_top`, `decorations: false`, `transparent: true`, `skip_taskbar: true`, `focusable: false`

### Positioning

1. Get system tray icon screen coordinates
2. Place Toast centered above tray icon with 8px gap
3. Fallback: bottom-right corner of primary monitor if tray position unavailable

### Startup Sequence

```
app.setup():
  1. Create hidden main window (existing)
  2. setup_tray() (existing)
  3. open_capsule_window() (existing)
  4. Delay 500ms → show_toast("AirType 已启动") (new)
```

The 500ms delay ensures the tray icon is fully initialized before reading its position.

### Animation Flow

```
1. Rust creates toast window (hidden)
2. JS fires "toast_ready" event → Rust shows window
3. JS: Fade-in 200ms (opacity 0→1, translateY 8px→0)
4. JS: Wait 2500ms
5. JS: Fade-out 300ms (opacity 1→0, translateY 0→-4px)
6. JS: Notify Rust to close window via close_toast_window command
```

### Reusable API

`toast.rs` exposes:

```rust
pub fn show_toast(app: &AppHandle, message: &str)
```

Currently only called with "AirType 已启动" at startup, but designed for future reuse (e.g., mode change notifications, hotkey change confirmations).

## Out of Scope

- User-configurable notification settings
- Notification queue / stacking multiple toasts
- Click actions on the toast
- Different toast types (error, warning, etc.)
