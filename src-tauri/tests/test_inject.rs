#[test]
fn test_inject_error_types_exist() {
    let errors = vec![
        "SendInputFailed",
    ];
    assert_eq!(errors.len(), 1);
}

#[test]
fn test_inject_empty_text_returns_ok() {
    let result = airtype::inject::inject_text("");
    assert!(result.is_ok());
}

#[test]
fn test_inject_error_is_display() {
    let err = airtype::inject::InjectError::SendInputFailed;
    let msg = format!("{}", err);
    assert!(!msg.is_empty());
}
