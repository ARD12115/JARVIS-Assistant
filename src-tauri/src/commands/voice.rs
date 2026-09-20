use serde::{Deserialize, Serialize};
use tauri::State;
use base64::{Engine as _, engine::general_purpose};

#[derive(Debug, Serialize, Deserialize)]
pub struct VoiceSTTRequest {
    pub audio_base64: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VoiceTTSRequest {
    pub text: String,
    pub voice: Option<String>,
}

#[tauri::command]
pub async fn voice_stt(
    request: VoiceSTTRequest,
    client: State<'_, reqwest::Client>,
) -> Result<String, String> {

    let audio_bytes = general_purpose::STANDARD
        .decode(&request.audio_base64)
        .map_err(|e| e.to_string())?;

    let form = reqwest::multipart::Form::new()
        .part("audio", reqwest::multipart::Part::bytes(audio_bytes)
            .file_name("audio.webm")
            .mime_str("audio/webm").unwrap());

    let resp = client
        .post("http://127.0.0.1:8765/voice/stt")
        .multipart(form)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let data: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data["text"].as_str().unwrap_or("").to_string())
}

#[tauri::command]
pub async fn voice_tts(
    request: VoiceTTSRequest,
    client: State<'_, reqwest::Client>,
) -> Result<String, String> {

    let resp = client
        .post("http://127.0.0.1:8765/voice/tts")
        .json(&request)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let audio_bytes = resp.bytes().await.map_err(|e| e.to_string())?;
    let base64_audio = general_purpose::STANDARD.encode(&audio_bytes);

    Ok(base64_audio)
}

#[tauri::command]
pub async fn list_voices(
    client: State<'_, reqwest::Client>,
) -> Result<serde_json::Value, String> {
    let resp = client
        .get("http://127.0.0.1:8765/voice/voices")
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let voices = resp.json().await.map_err(|e| e.to_string())?;
    Ok(voices)
}
