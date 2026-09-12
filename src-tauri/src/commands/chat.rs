use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, State};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatRequest {
    pub session_id: String,
    pub content: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatStreamChunk {
    pub content: String,
    pub done: bool,
    pub tool_calls: Option<Vec<ToolCall>>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ToolCall {
    pub id: String,
    pub r#type: String,
    pub function: ToolFunction,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ToolFunction {
    pub name: String,
    pub arguments: String,
}

#[tauri::command]
pub async fn send_message(
    app: AppHandle,
    request: ChatRequest,
) -> Result<(), String> {
    let client = reqwest::Client::new();
    let resp = client
        .post("http://127.0.0.1:8765/chat/stream")
        .json(&request)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let mut stream = resp.bytes_stream();
    use futures_util::StreamExt;

    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                let text = String::from_utf8_lossy(&chunk);
                for line in text.lines() {
                    if line.starts_with("data: ") {
                        let data = &line[6..];
                        if data.trim() == "[DONE]" {
                            app.emit("chat-stream", ChatStreamChunk {
                                content: String::new(),
                                done: true,
                                tool_calls: None,
                            }).ok();
                            return Ok(());
                        }
                        if let Ok(chunk_data) = serde_json::from_str::<ChatStreamChunk>(data) {
                            app.emit("chat-stream", chunk_data).ok();
                        }
                    }
                }
            }
            Err(e) => return Err(e.to_string()),
        }
    }

    Ok(())
}

#[tauri::command]
pub async fn create_session() -> Result<String, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post("http://127.0.0.1:8765/memory/new")
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    let data: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data["session_id"].as_str().unwrap_or("").to_string())
}

#[tauri::command]
pub async fn list_sessions() -> Result<Vec<SessionInfo>, String> {
    let client = reqwest::Client::new();
    let resp = client
        .get("http://127.0.0.1:8765/memory/sessions")
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    let sessions = resp.json().await.map_err(|e| e.to_string())?;
    Ok(sessions)
}

#[tauri::command]
pub async fn get_history(session_id: String) -> Result<Vec<HistoryMessage>, String> {
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("http://127.0.0.1:8765/memory/history/{}", session_id))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    let history = resp.json().await.map_err(|e| e.to_string())?;
    Ok(history)
}

#[tauri::command]
pub async fn load_session(session_id: String) -> Result<bool, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post("http://127.0.0.1:8765/memory/load")
        .json(&serde_json::json!({ "session_id": session_id }))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(resp.status().is_success())
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SessionInfo {
    pub session_id: String,
    pub started_at: String,
    pub turn_count: i32,
    pub preview: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HistoryMessage {
    pub role: String,
    pub content: String,
    pub tool_calls: Option<Vec<ToolCall>>,
    pub tool_call_id: Option<String>,
}