mod manager;
mod loader;
mod cache;

pub use manager::*;
pub use loader::*;
pub use cache::*;

use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum ResourceType {
    Texture,
    Audio,
    Font,
    Shader,
    Model,
    Text,
    Json,
    Binary,
}

#[derive(Debug, Clone)]
pub struct ResourceInfo {
    pub path: PathBuf,
    pub size: u64,
    pub last_modified: std::time::SystemTime,
    pub resource_type: ResourceType,
}

#[derive(Debug, thiserror::Error)]
pub enum ResourceError {
    #[error("File not found: {0}")]
    NotFound(PathBuf),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Decode error: {0}")]
    Decode(String),
    
    #[error("Invalid format: {0}")]
    InvalidFormat(String),
    
    #[error("Resource already loaded: {0}")]
    AlreadyLoaded(PathBuf),
}