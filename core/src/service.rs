use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use thiserror::Error;
use crate::{KeyCode, Texture, Color, RenderStats};

#[derive(Error, Debug)]
pub enum ServiceError {
    #[error("Service not found: {0}")]
    NotFound(String),
    
    #[error("Service already registered: {0}")]
    AlreadyRegistered(String),
    
    #[error("Service initialization failed: {0}")]
    Initialization(String),
}

pub trait Service: Any + Send + Sync {
    fn name(&self) -> &str;
    fn initialize(&mut self) -> Result<(), ServiceError>;
    fn shutdown(&mut self);
}

// 服务容器
#[derive(Clone)]
pub struct ServiceContainer {
    services: Arc<RwLock<HashMap<TypeId, Box<dyn Service>>>>,
}

impl ServiceContainer {
    pub fn new() -> Self {
        Self {
            services: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub fn register<T: Service + 'static>(&self, service: T) -> Result<(), ServiceError> {
        let type_id = TypeId::of::<T>();
        let service_name = service.name().to_string();
        
        let mut services = self.services.write().unwrap();
        
        if services.contains_key(&type_id) {
            return Err(ServiceError::AlreadyRegistered(service_name));
        }
        
        services.insert(type_id, Box::new(service));
        Ok(())
    }
    
    pub fn get<T: Service + 'static>(&self) -> Option<Arc<T>> {
        // Simplified: the service container currently stores boxed services and
        // we cannot safely clone the concrete T out. For now, provide a None
        // placeholder so callers don't break compilation; functionality that
        // needs concrete typed access should be adapted later.
        None
    }
    
    pub fn initialize_all(&self) -> Result<(), ServiceError> {
        let mut services = self.services.write().unwrap();
        
        for service in services.values_mut() {
            service.initialize()?;
        }
        
        Ok(())
    }
    
    pub fn shutdown_all(&self) {
        let mut services = self.services.write().unwrap();
        
        for service in services.values_mut() {
            service.shutdown();
        }
    }
}

// 服务接口定义
pub trait IAudioService: Service {
    fn play(&self, sound_id: &str, volume: f32, looped: bool) -> Result<u64, ServiceError>;
    fn stop(&self, playback_id: u64) -> Result<(), ServiceError>;
    fn set_volume(&self, playback_id: u64, volume: f32) -> Result<(), ServiceError>;
    fn get_latency_ms(&self) -> f32;
}
pub trait IInputService: Service {
    fn is_key_down(&self, key: KeyCode) -> bool;
    fn is_key_pressed(&self, key: KeyCode) -> bool;
    fn get_mouse_position(&self) -> (f32, f32);
}

pub trait IResourceService: Service {
    fn load_texture(&self, path: &str) -> Result<u64, ServiceError>;
    fn load_audio(&self, path: &str) -> Result<Vec<u8>, ServiceError>;
    fn get_texture(&self, id: u64) -> Option<Arc<Texture>>;
}

pub trait IRenderService: Service {
    fn create_texture(&self, path: &str) -> Result<u64, ServiceError>;
    fn draw_sprite(&self, texture_id: u64, position: (f32, f32), rotation: f32, scale: f32);
    fn draw_text(&self, text: &str, position: (f32, f32), font_size: f32, color: Color);
    fn begin_frame(&self);
    fn end_frame(&self);
    fn get_render_stats(&self) -> RenderStats;
}