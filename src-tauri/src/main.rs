mod commands;
mod python_sidecar;

use std::sync::Arc;
use tauri::Manager;
use python_sidecar::PythonSidecar;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let sidecar = Arc::new(PythonSidecar::new(app.handle())?);
            tauri::async_runtime::block_on(sidecar.start())?;
            app.manage(sidecar);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::chat::send_message,
            commands::chat::create_session,
            commands::chat::list_sessions,
            commands::chat::get_history,
            commands::chat::load_session,
            commands::voice::voice_stt,
            commands::voice::voice_tts,
            commands::voice::list_voices,
            commands::tools::list_tools,
            commands::tools::execute_tool,
            commands::memory::memory_list_sessions,
            commands::memory::memory_get_history,
            commands::memory::memory_load_session,
            commands::memory::memory_new_session,
            commands::memory::memory_search_memory,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}