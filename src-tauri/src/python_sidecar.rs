use std::process::{Command, Stdio};
use std::sync::Arc;
use tokio::sync::Mutex;
use tauri::Manager;

pub struct PythonSidecar {
    child: Arc<Mutex<Option<std::process::Child>>>,
    python_path: String,
    script_path: String,
}

impl PythonSidecar {
    pub fn new(app_handle: &tauri::AppHandle) -> Result<Self, Box<dyn std::error::Error>> {
        let resource_dir = app_handle
            .path()
            .resolve("../src-python", tauri::path::BaseDirectory::Resource)?
            .to_string_lossy()
            .to_string();

        let python_path = if cfg!(target_os = "windows") {
            format!("{}/.venv/Scripts/python.exe", resource_dir)
        } else {
            format!("{}/.venv/bin/python", resource_dir)
        };

        let script_path = format!("{}/main.py", resource_dir);

        Ok(Self {
            child: Arc::new(Mutex::new(None)),
            python_path,
            script_path,
        })
    }

    pub async fn start(&self) -> Result<(), Box<dyn std::error::Error>> {
        let mut child_guard = self.child.lock().await;
        
        if child_guard.is_some() {
            return Ok(()); // Already running
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

        // Give it a moment to start
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
        let child_guard = self.child.lock().await;
        child_guard.as_ref().map_or(false, |c| c.try_wait().is_ok())
    }
}

impl Drop for PythonSidecar {
    fn drop(&mut self) {
        // Best effort cleanup
        if let Ok(mut child_guard) = self.child.try_lock() {
            if let Some(mut child) = child_guard.take() {
                let _ = child.kill();
            }
        }
    }
}