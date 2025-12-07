use crate::error::{CoreError, Result};
use super::{Chart, loader::ChartLoader, parser::MalodyParser};
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartInfo {
    pub id: String,
    pub title: String,
    pub artist: String,
    pub creator: String,
    pub version: String,
    pub bpm: f64,
    pub difficulties: Vec<ChartDifficulty>,
    pub audio_path: Option<String>,
    pub background_path: Option<String>,
    pub source_file: String,  // 原始文件路径
    pub import_date: chrono::DateTime<chrono::Utc>,
    pub play_count: u32,
    pub last_played: Option<chrono::DateTime<chrono::Utc>>,
    pub rating: Option<f32>,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartDifficulty {
    pub name: String,
    pub level: u8,
    pub note_count: usize,
    pub duration: f64,
    pub file_path: String,  // 实际.mc文件的路径
    pub mode: u8,          // 0=4K, 1=5K, 2=6K, etc.
    pub columns: u8,
    pub preview: Option<ChartPreview>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartPreview {
    pub start_time: f64,
    pub duration: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartIndex {
    pub charts: HashMap<String, ChartInfo>,  // key: chart_id
    pub last_update: chrono::DateTime<chrono::Utc>,
    pub version: u32,
}

pub struct ChartManager {
    charts_dir: PathBuf,
    index_path: PathBuf,
    loader: ChartLoader,
    index: Arc<RwLock<ChartIndex>>,
}

impl ChartManager {
    pub fn new() -> Result<Self> {
        let project_dirs = ProjectDirs::from("com", "openrhythm", "OpenRhythm")
            .ok_or_else(|| CoreError::System("Failed to get project directories".to_string()))?;
        
        let charts_dir = project_dirs.data_dir().join("charts");
        let index_path = project_dirs.data_dir().join("chart_index.json");
        
        // 创建目录
        fs::create_dir_all(&charts_dir)?;
        
        // 加载或创建索引
        let index = if index_path.exists() {
            let content = fs::read_to_string(&index_path)?;
            serde_json::from_str(&content)?
        } else {
            ChartIndex {
                charts: HashMap::new(),
                last_update: chrono::Utc::now(),
                version: 1,
            }
        };
        
        Ok(Self {
            charts_dir,
            index_path,
            loader: ChartLoader::new(),
            index: Arc::new(RwLock::new(index)),
        })
    }
    
    pub fn import_mcz_file<P: AsRef<Path>>(&self, mcz_path: P) -> Result<Vec<ChartInfo>> {
        let mcz_path = mcz_path.as_ref();
        let file_name = mcz_path.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown");
        
        // 解压目录
        let extract_dir = self.charts_dir.join(file_name);
        if extract_dir.exists() {
            // 如果已存在，先删除旧版本
            fs::remove_dir_all(&extract_dir)?;
        }
        fs::create_dir_all(&extract_dir)?;
        
        // 解压MCZ文件
        self.extract_mcz(mcz_path, &extract_dir)?;
        
        // 扫描解压后的谱面文件
        let mut imported_charts = Vec::new();
        
        for entry in walkdir::WalkDir::new(&extract_dir) {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("mc") {
                match self.process_chart_file(path, mcz_path) {
                    Ok(chart_info) => {
                        imported_charts.push(chart_info);
                    }
                    Err(e) => {
                        log::warn!("Failed to process chart file {:?}: {}", path, e);
                    }
                }
            }
        }
        
        // 更新索引
        self.update_index()?;
        
        Ok(imported_charts)
    }
    
    fn extract_mcz(&self, mcz_path: &Path, extract_dir: &Path) -> Result<()> {
        let file = fs::File::open(mcz_path)?;
        let mut archive = zip::ZipArchive::new(file)?;
        
        for i in 0..archive.len() {
            let mut file = archive.by_index(i)?;
            let file_name = file.name();
            
            // 跳过目录项
            if file_name.ends_with('/') {
                continue;
            }
            
            let output_path = extract_dir.join(file_name);
            
            // 确保父目录存在
            if let Some(parent) = output_path.parent() {
                fs::create_dir_all(parent)?;
            }
            
            // 写入文件
            let mut output_file = fs::File::create(&output_path)?;
            std::io::copy(&mut file, &mut output_file)?;
        }
        
        Ok(())
    }
    
    fn process_chart_file(&self, chart_path: &Path, source_path: &Path) -> Result<ChartInfo> {
        // 解析谱面
        let chart = MalodyParser::parse_from_file(chart_path)?;
        let metadata = &chart.metadata;
        
        // 生成唯一ID
        let chart_id = self.generate_chart_id(&chart);
        
        // 创建难度信息
        let difficulty = ChartDifficulty {
            name: metadata.version.clone(),
            level: self.calculate_difficulty_level(&chart),
            note_count: chart.notes.len(),
            duration: chart.duration(),
            file_path: chart_path.to_string_lossy().to_string(),
            mode: metadata.mode,
            columns: metadata.columns,
            preview: metadata.preview_time.map(|time| ChartPreview {
                start_time: time,
                duration: 30.0, // 默认30秒预览
            }),
        };
        
        // 检查是否已存在相同ID的谱面
        let mut index = self.index.write().unwrap();
        
        if let Some(existing) = index.charts.get_mut(&chart_id) {
            // 更新现有谱面
            existing.difficulties.push(difficulty);
            existing.difficulties.sort_by_key(|d| d.level);
            existing.last_played = None;
            existing.play_count = 0;
            
            return Ok(existing.clone());
        }
        
        // 创建新的谱面信息
        let chart_info = ChartInfo {
            id: chart_id.clone(),
            title: metadata.title.clone(),
            artist: metadata.artist.clone(),
            creator: metadata.creator.clone(),
            version: metadata.version.clone(),
            bpm: metadata.bpm,
            difficulties: vec![difficulty],
            audio_path: metadata.audio.clone(),
            background_path: metadata.background.clone(),
            source_file: source_path.to_string_lossy().to_string(),
            import_date: chrono::Utc::now(),
            play_count: 0,
            last_played: None,
            rating: None,
            tags: self.generate_tags(&chart),
        };
        
        index.charts.insert(chart_id, chart_info.clone());
        
        Ok(chart_info)
    }
    
    fn generate_chart_id(&self, chart: &Chart) -> String {
        use sha2::{Sha256, Digest};
        
        let metadata = &chart.metadata;
        let id_string = format!(
            "{}_{}_{}_{}",
            metadata.title,
            metadata.artist,
            metadata.creator,
            metadata.version
        );
        
        let mut hasher = Sha256::new();
        hasher.update(id_string);
        let result = hasher.finalize();
        
        hex::encode(&result[..8])  // 使用前8字节作为ID
    }
    
    fn calculate_difficulty_level(&self, chart: &Chart) -> u8 {
        // 简单的难度计算算法
        let note_count = chart.notes.len() as f64;
        let duration = chart.duration();
        let density = note_count / duration.max(1.0);
        
        let avg_bpm = chart.metadata.bpm;
        
        // 考虑长按音符数量
        let hold_notes = chart.notes.iter()
            .filter(|n| n.note_type == super::model::NoteType::Hold)
            .count() as f64;
        
        // 难度计算公式（简化版）
        let base_level = (density * avg_bpm / 5000.0).sqrt() * 20.0;
        let hold_bonus = (hold_notes / note_count.max(1.0)) * 5.0;
        
        let level = (base_level + hold_bonus).clamp(1.0, 30.0);
        
        level.round() as u8
    }
    
    fn generate_tags(&self, chart: &Chart) -> Vec<String> {
        let mut tags = Vec::new();
        
        // 根据模式添加标签
        match chart.metadata.mode {
            0 => tags.push("4k".to_string()),
            1 => tags.push("5k".to_string()),
            2 => tags.push("6k".to_string()),
            3 => tags.push("7k".to_string()),
            4 => tags.push("8k".to_string()),
            _ => tags.push(format!("{}k", chart.metadata.columns)),
        }
        
        // 根据BPM添加标签
        let bpm = chart.metadata.bpm;
        if bpm >= 180.0 {
            tags.push("high-bpm".to_string());
        } else if bpm <= 100.0 {
            tags.push("low-bpm".to_string());
        }
        
        // 根据音符数量添加标签
        let note_count = chart.notes.len();
        if note_count >= 1000 {
            tags.push("long".to_string());
        } else if note_count <= 100 {
            tags.push("short".to_string());
        }
        
        // 根据长按音符比例添加标签
        let hold_ratio = chart.notes.iter()
            .filter(|n| n.note_type == super::model::NoteType::Hold)
            .count() as f32 / note_count.max(1) as f32;
        
        if hold_ratio > 0.3 {
            tags.push("hold-heavy".to_string());
        }
        
        tags
    }
    
    fn update_index(&self) -> Result<()> {
        let mut index = self.index.write().unwrap();
        index.last_update = chrono::Utc::now();
        
        let content = serde_json::to_string_pretty(&*index)?;
        fs::write(&self.index_path, content)?;
        
        Ok(())
    }
    
    pub fn get_all_charts(&self) -> Vec<ChartInfo> {
        let index = self.index.read().unwrap();
        index.charts.values().cloned().collect()
    }
    
    pub fn search_charts(&self, query: &str) -> Vec<ChartInfo> {
        let index = self.index.read().unwrap();
        let query_lower = query.to_lowercase();
        
        index.charts.values()
            .filter(|chart| {
                chart.title.to_lowercase().contains(&query_lower) ||
                chart.artist.to_lowercase().contains(&query_lower) ||
                chart.creator.to_lowercase().contains(&query_lower) ||
                chart.tags.iter().any(|tag| tag.contains(&query_lower))
            })
            .cloned()
            .collect()
    }
    
    pub fn get_chart_by_id(&self, id: &str) -> Option<ChartInfo> {
        let index = self.index.read().unwrap();
        index.charts.get(id).cloned()
    }
    
    pub fn load_chart_with_difficulty(&self, chart_id: &str, difficulty_name: &str) -> Result<Chart> {
        let chart_info = self.get_chart_by_id(chart_id)
            .ok_or_else(|| CoreError::Parse(format!("Chart not found: {}", chart_id)))?;
        
        let difficulty = chart_info.difficulties
            .iter()
            .find(|d| d.name == difficulty_name)
            .ok_or_else(|| CoreError::Parse(format!("Difficulty not found: {}", difficulty_name)))?;
        
        MalodyParser::parse_from_file(&difficulty.file_path)
    }
    
    pub fn delete_chart(&self, chart_id: &str) -> Result<()> {
        let mut index = self.index.write().unwrap();
        
        if let Some(chart_info) = index.charts.remove(chart_id) {
            // 尝试删除源文件（可选）
            let source_path = PathBuf::from(chart_info.source_file);
            if source_path.exists() && source_path.is_file() {
                // 仅删除解压的文件，不删除原始MCZ
                if let Some(parent) = source_path.parent() {
                    if parent.starts_with(&self.charts_dir) {
                        fs::remove_dir_all(parent).ok(); // 忽略错误
                    }
                }
            }
            
            self.update_index()?;
        }
        
        Ok(())
    }
    
    pub fn record_play(&self, chart_id: &str) -> Result<()> {
        let mut index = self.index.write().unwrap();
        
        if let Some(chart) = index.charts.get_mut(chart_id) {
            chart.play_count += 1;
            chart.last_played = Some(chrono::Utc::now());
        }
        
        self.update_index()?;
        Ok(())
    }
    
    pub fn set_rating(&self, chart_id: &str, rating: f32) -> Result<()> {
        let mut index = self.index.write().unwrap();
        
        if let Some(chart) = index.charts.get_mut(chart_id) {
            chart.rating = Some(rating.clamp(0.0, 5.0));
        }
        
        self.update_index()?;
        Ok(())
    }
}