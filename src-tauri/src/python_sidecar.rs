use std::process::{Command, Stdio};
use std::sync::Arc;
use tokio::sync::Mutex;
use tauri::Manager;
use std::path::PathBuf;

pub struct PythonSidecar {
    child: Arc<Mutex<Option<std::process::Child>>>,
    python_path: String,
    script_path: String,
}

impl PythonSidecar {
    pub fn new(app_handle: &tauri::AppHandle) -> Result<Self, Box<dyn std::error::Error>> {
        // In development, the Python files are at the project root
        // In production, they're in the resource directory
        let base_dir = std::env::current_dir()
            .ok()
            .and_then(|p| p.parent().map(|p| p.join("src_python")))
            .map(|p| p.to_string_lossy().to_string())
            .or_else(|| {
                app_handle
                    .path()
                    .resolve("../src_python", tauri::path::BaseDirectory::Resource)
                    .ok()
                    .map(|p| p.to_string_lossy().to_string())
            })
            .ok_or("Could not determine src_python directory")?;

        let python_path = if cfg!(target_os = "windows") {
            format!("{}/.venv/Scripts/python.exe", base_dir)
        } else {
            format!("{}/.venv/bin/python", base_dir)
        };

        let script_path = format!("{}/main.py", base_dir);

        // Verify paths exist
        if !std::path::Path::new(&python_path).exists() {
            return Err(format!("Python executable not found at: {}", python_path).into());
        }
        if !std::path::Path::new(&script_path).exists() {
            return Err(format!("Main script not found at: {}", script_path).into());
        }

        Ok(Self {
            child: Arc::new(Mutex::new(None)),
            python_path,
            script_path,
        })
    }

    pub async fn start(&self) -> Result<(), Box<dyn std::error::Error>> {
        let mut child_guard = self.child.lock().await;

        if child_guard.is_some() {
            return Ok(());
        }

        let mut cmd = Command::new(&self.python_path);
        cmd.arg(&self.script_path)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        let child = cmd.spawn()?;
        *child_guard = Some(child);

        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

        Ok(())
    }

    pub async fn stop(&self) -> Result<(), Box<dyn std::error::Error>> {
        let mut child_guard = self.child.lock().await;

        if let Some(mut child) = child_guard.take() {
            child.kill()?;
            child.wait()?;
        }

        Ok(())
    }

    pub async fn is_running(&self) -> bool {
        let mut child_guard = self.child.lock().await;
        if let Some(child) = child_guard.as_mut() {
            matches!(child.try_wait(), Ok(None))
        } else {
            false
        }
    }
}

impl Drop for PythonSidecar {
    fn drop(&mut self) {
        if let Ok(mut child_guard) = self.child.try_lock() {
            if let Some(mut child) = child_guard.take() {
                let _ = child.kill();
            }
        }
    }
}