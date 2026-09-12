mod commands;
mod python_sidecar;

use commands::{chat, memory, tools, voice};
use python_sidecar::PythonSidecar;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_global_shortcut::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // Initialize Python sidecar
            let python_sidecar = PythonSidecar::new(app.handle())?;
            
            // Start Python backend
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = python_sidecar.start().await {
                    eprintln!("Failed to start Python backend: {}", e);
                } else {
                    println!("Python backend started successfully");
                }
            });

            // Store sidecar for cleanup
            app.manage(python_sidecar);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Chat commands
            chat::send_message,
            chat::create_session,
            chat::list_sessions,
            chat::get_history,
            chat::load_session,
            // Voice commands
            voice::voice_stt,
            voice::voice_tts,
            voice::list_voices,
            // Tool commands
            tools::list_tools,
            tools::execute_tool,
            // Memory commands
            memory::list_sessions,
            memory::get_history,
            memory::load_session,
            memory::new_session,
            memory::search_memory,
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Clean up Python sidecar on close
                let sidecar: tauri::State<PythonSidecar> = window.state();
                tauri::async_runtime::block_on(async {
                    if let Err(e) = sidecar.stop().await {
                        eprintln!("Failed to stop Python backend: {}", e);
                    }
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}