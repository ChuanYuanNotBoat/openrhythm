use crate::service::{Service, ServiceError, IAudioService};
use crate::resource::ResourceManager;
use std::sync::{Arc, Mutex};
use std::path::Path;

use super::{
    decoder::AudioData,
    player::AudioPlayer,
    // 暂时注释掉低延迟引擎，因为它有线程安全问题
    // low_latency::LowLatencyAudioEngine,
};

pub struct AudioServiceImpl {
    player: Mutex<AudioPlayer>,
    // 暂时移除低延迟引擎
    // low_latency_engine: Option<Mutex<LowLatencyAudioEngine>>,
    resource_manager: Option<Arc<Mutex<ResourceManager>>>,  // 添加 Mutex
    use_low_latency: bool,
    audio_cache: Mutex<std::collections::HashMap<String, Arc<AudioData>>>,
}

impl AudioServiceImpl {
    pub fn new() -> Result<Self, ServiceError> {
        let player = AudioPlayer::new()
            .map_err(|e| ServiceError::Initialization(format!("Failed to create audio player: {}", e)))?;
        
        Ok(Self {
            player: Mutex::new(player),
            resource_manager: None,
            use_low_latency: false,  // 暂时禁用低延迟
            audio_cache: Mutex::new(std::collections::HashMap::new()),
        })
    }
    
    pub fn set_resource_manager(&mut self, resource_manager: Arc<Mutex<ResourceManager>>) {
        self.resource_manager = Some(resource_manager);
    }
    
    fn load_audio_data(&self, path: &str) -> Result<Arc<AudioData>, ServiceError> {
        // 检查缓存
        {
            let cache = self.audio_cache.lock()
                .map_err(|e| ServiceError::Initialization(format!("Failed to lock audio cache: {}", e)))?;
            if let Some(data) = cache.get(path) {
                return Ok(data.clone());
            }
        }
        
        // 从资源管理器加载
        let resource_manager = self.resource_manager.as_ref()
            .ok_or_else(|| ServiceError::Initialization("Resource manager not set".to_string()))?;
        
        // 获取资源管理器的锁
        let mut resource_manager = resource_manager.lock()
            .map_err(|e| ServiceError::Initialization(format!("Failed to lock resource manager: {}", e)))?;
        
        let audio_bytes = resource_manager.load_audio(Path::new(path))
            .map_err(|e| ServiceError::Initialization(format!("Failed to load audio: {}", e)))?;
        
        // 暂时从字节加载音频数据
        let temp_path = std::env::temp_dir().join(format!("audio_{}.tmp", path.replace("/", "_")));
        std::fs::write(&temp_path, &*audio_bytes)
            .map_err(|e| ServiceError::Initialization(format!("Failed to write temp audio file: {}", e)))?;
        
        let audio_data = AudioData::from_file(&temp_path)
            .map_err(|e| ServiceError::Initialization(format!("Failed to decode audio: {}", e)))?;
        
        let audio_data = Arc::new(audio_data);
        
        // 存入缓存
        {
            let mut cache = self.audio_cache.lock()
                .map_err(|e| ServiceError::Initialization(format!("Failed to lock audio cache: {}", e)))?;
            cache.insert(path.to_string(), audio_data.clone());
        }
        
        // 清理临时文件
        let _ = std::fs::remove_file(&temp_path);
        
        Ok(audio_data)
    }
}

impl Service for AudioServiceImpl {
    fn name(&self) -> &str {
        "audio"
    }
    
    fn initialize(&mut self) -> Result<(), ServiceError> {
        Ok(())
    }
    
    fn shutdown(&mut self) {
        if let Ok(mut player) = self.player.lock() {
            player.stop_all();
        }
    }
}

impl IAudioService for AudioServiceImpl {
    fn play(&self, sound_id: &str, volume: f32, looped: bool) -> Result<u64, ServiceError> {
        let audio_data = self.load_audio_data(sound_id)?;
        
        let mut player = self.player.lock()
            .map_err(|e| ServiceError::Initialization(format!("Failed to lock audio player: {}", e)))?;
        
        player.play_audio_data(&audio_data, volume, looped)
            .map_err(|e| ServiceError::Initialization(format!("Failed to play audio: {}", e)))
    }
    
    fn stop(&self, playback_id: u64) -> Result<(), ServiceError> {
        let mut player = self.player.lock()
            .map_err(|e| ServiceError::Initialization(format!("Failed to lock audio player: {}", e)))?;
        
        player.stop(playback_id)
            .map_err(|e| ServiceError::Initialization(format!("Failed to stop audio: {}", e)))
    }
    
    fn set_volume(&self, playback_id: u64, volume: f32) -> Result<(), ServiceError> {
        let mut player = self.player.lock()
            .map_err(|e| ServiceError::Initialization(format!("Failed to lock audio player: {}", e)))?;
        
        player.set_volume(playback_id, volume)
            .map_err(|e| ServiceError::Initialization(format!("Failed to set volume: {}", e)))
    }
    
    fn get_latency_ms(&self) -> f32 {
        // 标准播放器的估计延迟
        50.0 // 估计值
    }
}

impl AudioServiceImpl {
    pub fn preload_audio(&self, path: &str) -> Result<(), ServiceError> {
        self.load_audio_data(path)?;
        Ok(())
    }
    
    pub fn clear_cache(&self) {
        if let Ok(mut cache) = self.audio_cache.lock() {
            cache.clear();
        }
    }
    
    pub fn set_master_volume(&self, volume: f32) -> Result<(), ServiceError> {
        let mut player = self.player.lock()
            .map_err(|e| ServiceError::Initialization(format!("Failed to lock audio player: {}", e)))?;
        
        player.set_master_volume(volume);
        Ok(())
    }
}