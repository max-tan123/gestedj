// Learn more about Tauri commands at https://tauri.app/v1/guides/features/command
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn test_python_connection() -> String {
    // This will be used to test connection to Python backend
    "Python connection test from Tauri v2".to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet, test_python_connection])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}