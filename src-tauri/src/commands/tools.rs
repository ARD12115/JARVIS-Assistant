use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, State};

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolExecuteRequest {
    pub tool_name: String,
    pub params: serde_json::Value,
}

#[tauri::command]
pub async fn list_tools() -> Result<Vec<ToolInfo>, String> {
    let client = reqwest::Client::new();
    let resp = client
        .get("http://127.0.0.1:8765/tools")
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    let tools = resp.json().await.map_err(|e| e.to_string())?;
    Ok(tools)
}

#[tauri::command]
pub async fn execute_tool(request: ToolExecuteRequest) -> Result<ToolResult, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("http://127.0.0.1:8765/tools/{}", request.tool_name))
        .json(&request.params)
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    let result = resp.json().await.map_err(|e| e.to_string())?;
    Ok(result)
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolInfo {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value,
    pub returns: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ToolResult {
    pub success: bool,
    pub data: Option<serde_json::Value>,
    pub error: Option<String>,
}