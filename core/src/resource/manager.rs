use super::{cache::ResourceCache, loader::{ResourceLoader, TextureLoader, AudioLoader, TextLoader}, ResourceError, ResourceInfo, ResourceType};
use crate::rendering::Texture;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

pub struct ResourceManager {
    cache: ResourceCache,
    loaders: HashMap<ResourceType, Box<dyn ResourceLoader<Resource = Box<dyn std::any::Any + Send + Sync>> + Send + Sync>>,
    search_paths: Vec<PathBuf>,
}

impl ResourceManager {
    pub fn new(max_cache_size: usize) -> Self {
        Self {
            cache: ResourceCache::new(max_cache_size),
            loaders: HashMap::new(),
            search_paths: Vec::new(),
        }
    }
    
    pub fn add_search_path(&mut self, path: PathBuf) {
        self.search_paths.push(path);
    }
    
    pub fn register_loader<T>(&mut self, loader: T)
    where
        T: ResourceLoader + 'static,
        T::Resource: Send + Sync + 'static,
    {
        let loader = Box::new(GenericLoader(loader));
        self.loaders.insert(loader.resource_type(), loader);
    }
    
    pub fn find_file(&self, relative_path: &Path) -> Option<PathBuf> {
        // 首先检查相对路径本身
        if relative_path.exists() {
            return Some(relative_path.to_path_buf());
        }
        
        // 在搜索路径中查找
        for base_path in &self.search_paths {
            let full_path = base_path.join(relative_path);
            if full_path.exists() {
                return Some(full_path);
            }
        }
        
        None
    }
    
    pub fn load<T: Send + Sync + 'static>(&mut self, path: &Path) -> Result<Arc<T>, ResourceError> {
        let path_buf = self.find_file(path)
            .ok_or_else(|| ResourceError::NotFound(path.to_path_buf()))?;
        
        // 检查缓存
        if let Some(resource) = self.cache.get::<T>(&path_buf) {
            return Ok(resource);
        }
        
        // 获取文件信息
        let metadata = std::fs::metadata(&path_buf)
            .map_err(|e| ResourceError::Io(e))?;
        
        let info = ResourceInfo {
            path: path_buf.clone(),
            size: metadata.len(),
            last_modified: metadata.modified()
                .unwrap_or_else(|_| std::time::SystemTime::now()),
            resource_type: self.detect_resource_type(&path_buf),
        };
        
        // 查找合适的加载器
        let loader = self.find_loader(&path_buf)
            .ok_or_else(|| ResourceError::InvalidFormat(format!("No loader for file: {:?}", path_buf)))?;
        
        // 加载资源
        let resource = loader.load(&path_buf)?;

        // 插入缓存（clone path_buf 以避免后续借用问题）
        self.cache.insert(path_buf.clone(), resource, info)?;
        
        // 从缓存中获取（确保类型正确）
        self.cache.get::<T>(&path_buf)
            .ok_or_else(|| ResourceError::Decode("Failed to retrieve cached resource".to_string()))
    }
    
    pub fn load_texture(&mut self, path: &Path) -> Result<Arc<Texture>, ResourceError> {
        self.load(path)
    }
    
    pub fn load_text(&mut self, path: &Path) -> Result<Arc<String>, ResourceError> {
        self.load(path)
    }
    
    pub fn load_audio(&mut self, path: &Path) -> Result<Arc<Vec<u8>>, ResourceError> {
        self.load(path)
    }
    
    fn detect_resource_type(&self, path: &PathBuf) -> ResourceType {
        let ext = path.extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();
        
        match ext.as_str() {
            "png" | "jpg" | "jpeg" | "bmp" | "tga" | "gif" => ResourceType::Texture,
            "ogg" | "wav" | "mp3" | "flac" => ResourceType::Audio,
            "ttf" | "otf" => ResourceType::Font,
            "wgsl" | "glsl" | "vert" | "frag" => ResourceType::Shader,
            "json" => ResourceType::Json,
            "txt" | "toml" | "yaml" | "yml" | "xml" | "html" | "css" | "js" | "ts" => ResourceType::Text,
            _ => ResourceType::Binary,
        }
    }
    
    fn find_loader(&self, path: &PathBuf) -> Option<&Box<dyn ResourceLoader<Resource = Box<dyn std::any::Any + Send + Sync>> + Send + Sync>> {
        let resource_type = self.detect_resource_type(path);
        self.loaders.get(&resource_type)
    }
    
    pub fn cache_stats(&self) -> super::cache::CacheStats {
        self.cache.stats()
    }
    
    pub fn clear_cache(&mut self) {
        self.cache.clear();
    }
}

// 通用加载器包装
struct GenericLoader<T: ResourceLoader>(T);

impl<T: ResourceLoader> ResourceLoader for GenericLoader<T> {
    type Resource = Box<dyn std::any::Any + Send + Sync>;
    
    fn load(&self, path: &PathBuf) -> Result<Self::Resource, ResourceError> {
        let resource = self.0.load(path)?;
        Ok(Box::new(resource))
    }
    
    fn can_load(&self, path: &PathBuf) -> bool {
        self.0.can_load(path)
    }
    
    fn resource_type(&self) -> ResourceType {
        self.0.resource_type()
    }
}