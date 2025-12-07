use thiserror::Error;
use winit::error::OsError;
use std::path::PathBuf;

#[derive(Error, Debug)]
pub enum CoreError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Window creation error: {0}")]
    WindowCreation(#[from] OsError),

    #[error("Zipped archive error: {0}")]
    Zip(#[from] zip::result::ZipError),

    #[error("Serde JSON error: {0}")]
    SerdeJson(#[from] serde_json::Error),

    #[error("Walkdir error: {0}")]
    WalkDir(#[from] walkdir::Error),

    #[error("Audio default config error: {0}")]
    DefaultStreamConfig(#[from] cpal::DefaultStreamConfigError),

    #[error("Audio build stream error: {0}")]
    BuildStream(#[from] cpal::BuildStreamError),

    #[error("Audio play stream error: {0}")]
    PlayStream(#[from] cpal::PlayStreamError),
    
    #[error("Graphics initialization error: {0}")]
    Graphics(String),

    #[error("WGPU surface creation error: {0}")]
    CreateSurface(#[from] wgpu::CreateSurfaceError),
    
    #[error("Audio initialization error: {0}")]
    Audio(String),
    
    #[error("Mod loading error: {0}")]
    ModLoading(String),
    
    #[error("Resource error: {0}")]
    Resource(String),
    
    #[error("Invalid path: {0}")]
    InvalidPath(PathBuf),
    
    #[error("Parse error: {0}")]
    Parse(String),
    
    #[error("System error: {0}")]
    System(String),
}

pub type Result<T> = std::result::Result<T, CoreError>;