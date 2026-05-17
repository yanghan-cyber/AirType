use crate::{config, llm, log::log_debug};

/// Run LLM processing with fallback to original text on failure.
/// Returns the text to inject (LLM result or original text).
pub fn run_llm_with_fallback(
    text: &str,
    cfg: &config::AppConfig,
    mode: &config::ProcessingMode,
) -> Result<String, String> {
    if mode.id == "direct" {
        return Ok(text.to_string());
    }

    let llm_client = llm::LlmClient::new(cfg.llm.clone());
    let user_content = mode.apply_template(text);

    match llm_client.chat_completion(&mode.system_prompt, &user_content) {
        Ok(response) => Ok(response.content),
        Err(e) => {
            log_debug(&format!("[llm] Error: {}, falling back to original text", e));
            Ok(text.to_string())
        }
    }
}
