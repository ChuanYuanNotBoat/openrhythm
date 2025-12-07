use super::{ResourceError, ResourceInfo, ResourceType};
use crate::rendering::Texture;
use std::path::PathBuf;
use std::sync::Arc;

pub trait ResourceLoader: Send + Sync {
    type Resource: Send + Sync + 'static;

    fn load(&self, path: &PathBuf) -> Result<Self::Resource, ResourceError>;
    fn can_load(&self, path: &PathBuf) -> bool;
    fn resource_type(&self) -> ResourceType;
}

pub struct TextureLoader {
    device: Arc<wgpu::Device>,
    queue: Arc<wgpu::Queue>,
}

impl TextureLoader {
    pub fn new(device: Arc<wgpu::Device>, queue: Arc<wgpu::Queue>) -> Self {
        Self { device, queue }
    }
}

impl ResourceLoader for TextureLoader {
    type Resource = Texture;
    
    fn load(&self, path: &PathBuf) -> Result<Self::Resource, ResourceError> {
        // 读取图片文件
        let bytes = std::fs::read(path)
            .map_err(|e| ResourceError::Io(e))?;
        
        // 使用image库解码
        let image = image::load_from_memory(&bytes)
            .map_err(|e| ResourceError::Decode(format!("Failed to load image: {}", e)))?;
        
        let rgba = image.to_rgba8();
        let width = rgba.width();
        let height = rgba.height();
        
        // 创建纹理
        Texture::from_bytes(
            self.device.clone(),
            self.queue.clone(),
            &rgba,
            width,
            height,
            Some(path.to_str().unwrap_or("texture")),
        )
        .map_err(|e| ResourceError::Decode(format!("Failed to create texture: {}", e)))
    }
    
    fn can_load(&self, path: &PathBuf) -> bool {
        let ext = path.extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();
        
        matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "bmp" | "tga" | "gif")
    }
    
    fn resource_type(&self) -> ResourceType {
        ResourceType::Texture
    }
}

pub struct AudioLoader;

impl ResourceLoader for AudioLoader {
    type Resource = Vec<u8>;
    
    fn load(&self, path: &PathBuf) -> Result<Self::Resource, ResourceError> {
        std::fs::read(path)
            .map_err(|e| ResourceError::Io(e))
    }
    
    fn can_load(&self, path: &PathBuf) -> bool {
        let ext = path.extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();
        
        matches!(ext.as_str(), "ogg" | "wav" | "mp3" | "flac")
    }
    
    fn resource_type(&self) -> ResourceType {
        ResourceType::Audio
    }
}

pub struct TextLoader;

impl ResourceLoader for TextLoader {
    type Resource = String;
    
    fn load(&self, path: &PathBuf) -> Result<Self::Resource, ResourceError> {
        std::fs::read_to_string(path)
            .map_err(|e| ResourceError::Io(e))
    }
    
    fn can_load(&self, path: &PathBuf) -> bool {
        let ext = path.extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();
        
        matches!(ext.as_str(), "txt" | "json" | "toml" | "yaml" | "yml" | "xml" | "html" | "css" | "js" | "ts")
    }
    
    fn resource_type(&self) -> ResourceType {
        ResourceType::Text
    }
}