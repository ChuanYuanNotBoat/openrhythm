use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartMetadata {
    pub title: String,
    pub title_original: Option<String>,
    pub artist: String,
    pub artist_original: Option<String>,
    pub creator: String,
    pub version: String,
    pub background: Option<String>,
    pub audio: Option<String>,
    pub audio_offset: i32, // 偏移量，单位毫秒
    pub preview_time: Option<f64>, // 预览开始时间，单位秒
    pub bpm: f64,
    pub id: Option<u64>,
    pub mode: u8, // 0=4K, 1=5K, 2=6K, 3=7K, 4=8K
    pub columns: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BPMChange {
    pub time: f64, // 时间，单位秒
    pub bpm: f64,
    pub beat: (i32, i32, i32), // 小节，分子，分母
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeSignature {
    pub time: f64, // 时间，单位秒
    pub numerator: u8, // 拍号分子
    pub denominator: u8, // 拍号分母
    pub beat: (i32, i32, i32),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeedChange {
    pub time: f64, // 时间，单位秒
    pub speed: f64, // 流速倍率
    pub beat: (i32, i32, i32),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NoteType {
    Tap,    // 单点
    Hold,   // 长按
    Slide,  // 滑动
    Chain,  // 连打
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Note {
    pub id: u64,
    pub start_time: f64,      // 开始时间，单位秒
    pub end_time: Option<f64>, // 结束时间（长按），单位秒
    pub column: u8,           // 轨道（0-based）
    pub note_type: NoteType,
    pub beat: (i32, i32, i32), // 拍数 [小节, 分子, 分母]
    pub sound: Option<String>, // 自定义音效
    pub volume: Option<u8>,    // 音量
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chart {
    pub metadata: ChartMetadata,
    pub bpm_changes: Vec<BPMChange>,
    pub time_signatures: Vec<TimeSignature>,
    pub speed_changes: Vec<SpeedChange>,
    pub notes: Vec<Note>,
    pub effects: Vec<ChartEvent>,
    pub custom_data: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartEvent {
    pub time: f64,
    pub event_type: String,
    pub data: serde_json::Value,
}

impl Chart {
    pub fn new(metadata: ChartMetadata) -> Self {
        Self {
            metadata,
            bpm_changes: Vec::new(),
            time_signatures: Vec::new(),
            speed_changes: Vec::new(),
            notes: Vec::new(),
            effects: Vec::new(),
            custom_data: HashMap::new(),
        }
    }
    
    pub fn duration(&self) -> f64 {
        self.notes
            .iter()
            .map(|note| note.end_time.unwrap_or(note.start_time))
            .fold(0.0, |max, time| max.max(time))
    }
    
    pub fn total_notes(&self) -> usize {
        self.notes.len()
    }
    
    pub fn get_note_density(&self, window_seconds: f64) -> Vec<f64> {
        if self.notes.is_empty() {
            return Vec::new();
        }
        
        let duration = self.duration();
        let num_windows = (duration / window_seconds).ceil() as usize + 1;
        let mut density = vec![0.0; num_windows];
        
        for note in &self.notes {
            let window_index = (note.start_time / window_seconds).floor() as usize;
            if window_index < num_windows {
                density[window_index] += 1.0;
            }
        }
        
        // 转换为每秒音符数
        for d in &mut density {
            *d /= window_seconds;
        }
        
        density
    }
    
    pub fn get_bpm_at_time(&self, time: f64) -> f64 {
        let mut current_bpm = self.metadata.bpm;
        
        for change in &self.bpm_changes {
            if change.time <= time {
                current_bpm = change.bpm;
            } else {
                break;
            }
        }
        
        current_bpm
    }
    
    pub fn beat_to_time(&self, beat: (i32, i32, i32)) -> f64 {
        let (measure, numerator, denominator) = beat;
        let total_beats = measure as f64 + numerator as f64 / denominator as f64;
        
        // 根据BPM变化计算时间
        let mut time = 0.0;
        let mut current_beat = 0.0;
        let mut current_bpm = self.metadata.bpm;
        
        for change in &self.bpm_changes {
            let beats_until_change = change.beat.0 as f64 + change.beat.1 as f64 / change.beat.2 as f64 - current_beat;
            let time_until_change = beats_until_change * (60.0 / current_bpm);
            
            if current_beat + beats_until_change <= total_beats {
                time += time_until_change;
                current_beat += beats_until_change;
                current_bpm = change.bpm;
            } else {
                let remaining_beats = total_beats - current_beat;
                time += remaining_beats * (60.0 / current_bpm);
                current_beat = total_beats;
                break;
            }
        }
        
        if current_beat < total_beats {
            let remaining_beats = total_beats - current_beat;
            time += remaining_beats * (60.0 / current_bpm);
        }
        
        time
    }
}