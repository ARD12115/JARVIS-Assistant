use serde::{Deserialize, Serialize};
use tauri::State;

#[tauri::command]
pub async fn memory_list_sessions(
    client: State<'_, reqwest::Client>,
) -> Result<Vec<SessionInfo>, String> {
    let resp = client
        .get("http://127.0.0.1:8765/memory/sessions")
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let sessions = resp.json().await.map_err(|e| e.to_string())?;
    Ok(sessions)
}

#[tauri::command]
pub async fn memory_get_history(
    session_id: String,
    limit: Option<i32>,
    client: State<'_, reqwest::Client>,
) -> Result<Vec<HistoryMessage>, String> {
    let url = format!(
        "http://127.0.0.1:8765/memory/history/{}?limit={}",
        session_id,
        limit.unwrap_or(50)
    );
    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let history = resp.json().await.map_err(|e| e.to_string())?;
    Ok(history)
}

#[tauri::command]
pub async fn memory_load_session(
    session_id: String,
    client: State<'_, reqwest::Client>,
) -> Result<bool, String> {
    let resp = client
        .post("http://127.0.0.1:8765/memory/load")
        .json(&serde_json::json!({ "session_id": session_id }))
        .send()
        .await
        .map_err(|e| e.to_string())?;

    Ok(resp.status().is_success())
}

#[tauri::command]
pub async fn memory_new_session(
    client: State<'_, reqwest::Client>,
) -> Result<String, String> {
    let resp = client
        .post("http://127.0.0.1:8765/memory/new")
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let data: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data["session_id"].as_str().unwrap_or("").to_string())
}

#[tauri::command]
pub async fn memory_search_memory(
    session_id: String,
    query: String,
    limit: Option<i32>,
    client: State<'_, reqwest::Client>,
) -> Result<Vec<HistoryMessage>, String> {
    let resp = client
        .get("http://127.0.0.1:8765/memory/search")
        .query(&[
            ("session_id", session_id),
            ("query", query),
            ("limit", limit.unwrap_or(10).to_string())
        ])
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let results = resp.json().await.map_err(|e| e.to_string())?;
    Ok(results)
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

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: String,
    pub r#type: String,
    pub function: ToolFunction,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolFunction {
    pub name: String,
    pub arguments: String,
}







