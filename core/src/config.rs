use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreConfig {
    pub window: WindowConfig,
    pub audio: AudioConfig,
    pub paths: PathConfig,
    pub debug: DebugConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowConfig {
    pub width: u32,
    pub height: u32,
    pub fullscreen: bool,
    pub vsync: bool,
    pub fps_limit: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioConfig {
    pub sample_rate: u32,
    pub buffer_size: u32,
    pub latency_target_ms: u32,
    pub master_volume: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathConfig {
    pub mods_dir: PathBuf,
    pub assets_dir: PathBuf,
    pub config_dir: PathBuf,
    pub logs_dir: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugConfig {
    pub show_fps: bool,
    pub show_debug_info: bool,
    pub log_level: String,
}

impl Default for CoreConfig {
    fn default() -> Self {
        Self {
            window: WindowConfig::default(),
            audio: AudioConfig::default(),
            paths: PathConfig::default(),
            debug: DebugConfig::default(),
        }
    }
}

impl Default for WindowConfig {
    fn default() -> Self {
        Self {
            width: 1280,
            height: 720,
            fullscreen: false,
            vsync: true,
            fps_limit: 0,
        }
    }
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            sample_rate: 48000,
            buffer_size: 2048,
            latency_target_ms: 30,
            master_volume: 1.0,
        }
    }
}

impl Default for PathConfig {
    fn default() -> Self {
        Self {
            mods_dir: PathBuf::from("mods"),
            assets_dir: PathBuf::from("assets"),
            config_dir: PathBuf::from("config"),
            logs_dir: PathBuf::from("logs"),
        }
    }
}

impl Default for DebugConfig {
    fn default() -> Self {
        Self {
            show_fps: false,
            show_debug_info: false,
            log_level: "info".to_string(),
        }
    }
}