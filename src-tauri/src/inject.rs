#[derive(Debug)]
pub enum InjectError {
    SendInputFailed,
}

impl std::fmt::Display for InjectError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            InjectError::SendInputFailed => write!(f, "模拟按键失败"),
        }
    }
}

impl std::error::Error for InjectError {}

/// Check if current keyboard layout is CJK.
#[cfg(target_os = "windows")]
fn is_cjk_ime() -> bool {
    use windows::Win32::UI::Input::KeyboardAndMouse::GetKeyboardLayout;
    unsafe {
        let layout = GetKeyboardLayout(0);
        let lang_id = (layout.0 as u32) & 0xFFFF;
        let primary = lang_id & 0xFF;
        // 0x04=Chinese, 0x11=Japanese, 0x12=Korean
        matches!(primary, 0x04 | 0x11 | 0x12)
    }
}

#[cfg(not(target_os = "windows"))]
fn is_cjk_ime() -> bool {
    false
}

/// Inject text using SendInput with KEYEVENTF_UNICODE.
/// Sends each character as a Unicode key event, bypassing keyboard layout.
/// Works in CLI, terminals, and all standard Windows applications.
#[cfg(target_os = "windows")]
pub fn inject_text(text: &str) -> Result<(), InjectError> {
    use windows::Win32::UI::Input::KeyboardAndMouse::{
        ActivateKeyboardLayout, GetKeyboardLayout, LoadKeyboardLayoutW, SendInput,
        INPUT, INPUT_0, INPUT_TYPE, KEYBDINPUT,
        KEYEVENTF_KEYUP, KEYEVENTF_UNICODE, VIRTUAL_KEY, KLF_ACTIVATE,
    };
    use windows::core::PCWSTR;

    if text.is_empty() {
        return Ok(());
    }

    unsafe {
        let original_layout = GetKeyboardLayout(0);

        // Temporarily switch to English layout if CJK IME is active
        let switched = if is_cjk_ime() {
            let name = windows::core::HSTRING::from("00000409");
            LoadKeyboardLayoutW(PCWSTR(name.as_ptr()), KLF_ACTIVATE).is_ok()
        } else {
            false
        };

        // Encode text to UTF-16 and build key events (keydown + keyup per character)
        let chars: Vec<u16> = text.encode_utf16().collect();
        let mut inputs: Vec<INPUT> = Vec::with_capacity(chars.len() * 2);

        for &ch in &chars {
            inputs.push(INPUT {
                r#type: INPUT_TYPE(1),
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VIRTUAL_KEY(0),
                        wScan: ch,
                        dwFlags: KEYEVENTF_UNICODE,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            });
            inputs.push(INPUT {
                r#type: INPUT_TYPE(1),
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VIRTUAL_KEY(0),
                        wScan: ch,
                        dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            });
        }

        let sent = SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);

        // Restore original keyboard layout
        if switched {
            let _ = ActivateKeyboardLayout(original_layout, KLF_ACTIVATE);
        }

        if sent == 0 {
            return Err(InjectError::SendInputFailed);
        }
    }

    Ok(())
}

#[cfg(not(target_os = "windows"))]
pub fn inject_text(_text: &str) -> Result<(), InjectError> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inject_error_display_messages() {
        assert!(InjectError::SendInputFailed.to_string().contains("按键"));
    }

    #[test]
    fn test_inject_empty_text_is_ok() {
        assert!(inject_text("").is_ok());
    }

    #[test]
    fn test_inject_error_is_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<InjectError>();
    }
}
