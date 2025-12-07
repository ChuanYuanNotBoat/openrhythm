use super::{ResourceError, ResourceInfo, ResourceType};
use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, RwLock};

pub struct ResourceCache {
    cache: RwLock<HashMap<PathBuf, CacheEntry>>,
    max_size: usize,
    current_size: usize,
}

struct CacheEntry {
    resource: Box<dyn Any + Send + Sync>,
    info: ResourceInfo,
    last_accessed: std::time::Instant,
    size: usize,
}

impl ResourceCache {
    pub fn new(max_size: usize) -> Self {
        Self {
            cache: RwLock::new(HashMap::new()),
            max_size,
            current_size: 0,
        }
    }
    
    pub fn get<T: Send + Sync + 'static>(&self, path: &PathBuf) -> Option<Arc<T>> {
        let cache = self.cache.read().unwrap();
        cache.get(path).and_then(|entry| {
            // 资源以 `Arc<T>` 存储，尝试向下转型为 `Arc<T>` 并返回克隆的 Arc
            entry.resource.downcast_ref::<Arc<T>>().map(|arc| Arc::clone(arc))
        })
    }
    
    pub fn insert<T: Send + Sync + 'static>(
        &mut self,
        path: PathBuf,
        resource: T,
        info: ResourceInfo,
    ) -> Result<(), ResourceError> {
        let size = std::mem::size_of::<T>();
        
        // 检查是否已存在
        {
            let cache = self.cache.read().unwrap();
            if cache.contains_key(&path) {
                return Err(ResourceError::AlreadyLoaded(path));
            }
        }
        
        // 检查缓存大小，如果需要则清除
        if self.current_size + size > self.max_size {
            self.evict_oldest();
        }
        
        let entry = CacheEntry {
            resource: Box::new(Arc::new(resource)),
            info,
            last_accessed: std::time::Instant::now(),
            size,
        };
        
        {
            let mut cache = self.cache.write().unwrap();
            cache.insert(path, entry);
        }
        
        self.current_size += size;
        
        Ok(())
    }
    
    pub fn remove(&mut self, path: &PathBuf) -> Option<Box<dyn Any + Send + Sync>> {
        let mut cache = self.cache.write().unwrap();
        cache.remove(path).map(|entry| {
            self.current_size -= entry.size;
            entry.resource
        })
    }
    
    pub fn clear(&mut self) {
        let mut cache = self.cache.write().unwrap();
        cache.clear();
        self.current_size = 0;
    }
    
    pub fn contains(&self, path: &PathBuf) -> bool {
        let cache = self.cache.read().unwrap();
        cache.contains_key(path)
    }
    
    pub fn info(&self, path: &PathBuf) -> Option<ResourceInfo> {
        let cache = self.cache.read().unwrap();
        cache.get(path).map(|entry| entry.info.clone())
    }
    
    pub fn stats(&self) -> CacheStats {
        let cache = self.cache.read().unwrap();
        CacheStats {
            total_resources: cache.len(),
            total_size: self.current_size,
            max_size: self.max_size,
        }
    }
    
    fn evict_oldest(&mut self) {
        let mut cache = self.cache.write().unwrap();
        
        if let Some((oldest_path, _)) = cache.iter().min_by_key(|(_, entry)| entry.last_accessed) {
            let path = oldest_path.clone();
            if let Some(entry) = cache.remove(&path) {
                self.current_size -= entry.size;
            }
        }
    }
}

#[derive(Debug, Clone)]
pub struct CacheStats {
    pub total_resources: usize,
    pub total_size: usize,
    pub max_size: usize,
}