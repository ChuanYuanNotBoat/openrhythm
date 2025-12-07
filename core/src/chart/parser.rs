use crate::error::{CoreError, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

use super::model::*;

#[derive(Debug, Deserialize)]
struct MalodyMeta {
    #[serde(rename = "$ver")]
    ver: Option<i32>,
    creator: String,
    background: Option<String>,
    version: String,
    id: Option<u64>,
    mode: u8,
    time: Option<u64>,
    song: MalodySong,
    mode_ext: Option<MalodyModeExt>,
}

#[derive(Debug, Deserialize)]
struct MalodySong {
    title: String,
    artist: String,
    #[serde(default)]
    titleorg: Option<String>,
    #[serde(default)]
    artistorg: Option<String>,
    id: Option<u64>,
}

#[derive(Debug, Deserialize)]
struct MalodyModeExt {
    column: u8,
    bar_begin: Option<i32>,
}

#[derive(Debug, Deserialize)]
struct MalodyTimePoint {
    beat: [i32; 3],
    bpm: f64,
}

#[derive(Debug, Deserialize)]
struct MalodyNote {
    beat: [i32; 3],
    column: u8,
    sound: Option<String>,
    vol: Option<u8>,
    offset: Option<i32>,
    #[serde(rename = "type")]
    note_type: Option<u8>,
    end: Option<[i32; 3]>,
}

#[derive(Debug, Deserialize)]
struct MalodyEffect {
    beat: [i32; 3],
    #[serde(rename = "type")]
    effect_type: u8,
    value: f64,
}

#[derive(Debug, Deserialize)]
struct MalodyChart {
    meta: MalodyMeta,
    time: Vec<MalodyTimePoint>,
    effect: Vec<MalodyEffect>,
    note: Vec<MalodyNote>,
    extra: Option<HashMap<String, serde_json::Value>>,
}

pub struct MalodyParser;

impl MalodyParser {
    pub fn parse_from_str(json_str: &str) -> Result<Chart> {
        let malody_chart: MalodyChart = serde_json::from_str(json_str)
            .map_err(|e| CoreError::Parse(format!("Failed to parse Malody chart JSON: {}", e)))?;
        
        Self::convert_to_chart(malody_chart)
    }
    
    pub fn parse_from_file<P: AsRef<Path>>(path: P) -> Result<Chart> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| CoreError::Io(e))?;
        
        Self::parse_from_str(&content)
    }
    
    pub fn parse_from_bytes(bytes: &[u8]) -> Result<Chart> {
        let json_str = std::str::from_utf8(bytes)
            .map_err(|e| CoreError::Parse(format!("Invalid UTF-8 in chart data: {}", e)))?;
        
        Self::parse_from_str(json_str)
    }
    
    fn convert_to_chart(malody_chart: MalodyChart) -> Result<Chart> {
        let meta = &malody_chart.meta;
        let mode_ext = meta.mode_ext.as_ref();
        
        // 创建元数据
        let mut metadata = ChartMetadata {
            title: meta.song.title.clone(),
            title_original: meta.song.titleorg.clone(),
            artist: meta.song.artist.clone(),
            artist_original: meta.song.artistorg.clone(),
            creator: meta.creator.clone(),
            version: meta.version.clone(),
            background: meta.background.clone(),
            audio: None, // 会在解析音符时设置
            audio_offset: 0,
            preview_time: None,
            bpm: 120.0, // 默认值，会被第一个BPM点覆盖
            id: meta.id,
            mode: meta.mode,
            columns: mode_ext.map(|ext| ext.column).unwrap_or(4),
        };
        
        // 解析BPM变化
        let mut bpm_changes = Vec::new();
        let mut time_signatures = Vec::new();
        
        for time_point in &malody_chart.time {
            let beat = (time_point.beat[0], time_point.beat[1], time_point.beat[2]);
            
            // 第一个BPM点设置为主BPM
            if bpm_changes.is_empty() {
                metadata.bpm = time_point.bpm;
            }
            
            // 计算时间
            let time = Self::beat_to_time_with_bpm_changes(&bpm_changes, beat, metadata.bpm);
            
            bpm_changes.push(BPMChange {
                time,
                bpm: time_point.bpm,
                beat,
            });
            
            // 检查是否为拍号变化（Malody中拍号变化也通过time数组表示，但格式不同）
            // 这里简化处理，假设所有time条目都是BPM变化
        }
        
        // 解析效果（包括SV）
        let mut speed_changes = Vec::new();
        let mut effects = Vec::new();
        
        for effect in &malody_chart.effect {
            let beat = (effect.beat[0], effect.beat[1], effect.beat[2]);
            let time = Self::beat_to_time_with_bpm_changes(&bpm_changes, beat, metadata.bpm);
            
            match effect.effect_type {
                1 => {
                    // BPM变化（Malody中BPM变化也可以在effect中）
                    bpm_changes.push(BPMChange {
                        time,
                        bpm: effect.value,
                        beat,
                    });
                }
                2 => {
                    // 时间签名变化 - 修复算术溢出
                    let value = effect.value as u64;  // 先转换为 u64
                    let numerator = (value as u8) & 0xFF;
                    let denominator = ((value >> 8) as u8) & 0xFF;
                    
                    time_signatures.push(TimeSignature {
                        time,
                        numerator,
                        denominator,
                        beat,
                    });
                }
                3 => {
                    // 流速变化（SV）
                    speed_changes.push(SpeedChange {
                        time,
                        speed: effect.value,
                        beat,
                    });
                }
                _ => {
                    // 其他效果
                    effects.push(ChartEvent {
                        time,
                        event_type: format!("malody_effect_{}", effect.effect_type),
                        data: serde_json::json!({ "value": effect.value }),
                    });
                }
            }
        }

        
        // 解析音符
        let mut notes = Vec::new();
        let mut audio_files = HashMap::new();
        
        for (i, malody_note) in malody_chart.note.iter().enumerate() {
            let beat = (malody_note.beat[0], malody_note.beat[1], malody_note.beat[2]);
            let start_time = Self::beat_to_time_with_bpm_changes(&bpm_changes, beat, metadata.bpm);
            
            // 确定音符类型
            let note_type = match malody_note.note_type {
                Some(1) => NoteType::Hold,
                Some(2) => NoteType::Slide,
                Some(3) => NoteType::Chain,
                _ => NoteType::Tap,
            };
            
            // 计算结束时间（对于长按音符）
            let end_time = malody_note.end.map(|end_beat| {
                let end_beat_tuple = (end_beat[0], end_beat[1], end_beat[2]);
                Self::beat_to_time_with_bpm_changes(&bpm_changes, end_beat_tuple, metadata.bpm)
            });
            
            // 检查是否为音频文件引用
            if let Some(ref sound) = malody_note.sound {
                if note_type == NoteType::Tap && malody_note.column == 0 && i == 0 {
                    // 第一个轨道0的tap音符通常是音频文件引用
                    metadata.audio = Some(sound.clone());
                    metadata.audio_offset = malody_note.offset.unwrap_or(0);
                    continue; // 跳过这个"音符"，它只是音频引用
                } else {
                    // 记录音效文件
                    audio_files.insert(i, sound.clone());
                }
            }
            
            let note = Note {
                id: i as u64,
                start_time,
                end_time,
                column: malody_note.column,
                note_type,
                beat,
                sound: malody_note.sound.clone(),
                volume: malody_note.vol,
            };
            
            notes.push(note);
        }
        
        // 处理自定义数据
        let mut custom_data = HashMap::new();
        if let Some(extra) = malody_chart.extra {
            for (key, value) in extra {
                custom_data.insert(key, value);
            }
        }
        
        // 添加音频文件信息到自定义数据
        if !audio_files.is_empty() {
            custom_data.insert("audio_files".to_string(), serde_json::json!(audio_files));
        }
        
        // 创建图表
        let mut chart = Chart {
            metadata,
            bpm_changes,
            time_signatures,
            speed_changes,
            notes,
            effects,
            custom_data,
        };
        
        // 按开始时间排序所有内容
        chart.bpm_changes.sort_by(|a, b| a.time.partial_cmp(&b.time).unwrap());
        chart.time_signatures.sort_by(|a, b| a.time.partial_cmp(&b.time).unwrap());
        chart.speed_changes.sort_by(|a, b| a.time.partial_cmp(&b.time).unwrap());
        chart.notes.sort_by(|a, b| a.start_time.partial_cmp(&b.start_time).unwrap());
        chart.effects.sort_by(|a, b| a.time.partial_cmp(&b.time).unwrap());
        
        Ok(chart)
    }
    
    fn beat_to_time_with_bpm_changes(
        bpm_changes: &[BPMChange],
        target_beat: (i32, i32, i32),
        default_bpm: f64,
    ) -> f64 {
        let target_beats = target_beat.0 as f64 + target_beat.1 as f64 / target_beat.2 as f64;
        
        if bpm_changes.is_empty() {
            return target_beats * (60.0 / default_bpm);
        }
        
        let mut time = 0.0;
        let mut current_beat = 0.0;
        let mut current_bpm = default_bpm;
        
        for change in bpm_changes {
            let change_beats = change.beat.0 as f64 + change.beat.1 as f64 / change.beat.2 as f64;
            
            if change_beats <= target_beats {
                let beats_until_change = change_beats - current_beat;
                let time_until_change = beats_until_change * (60.0 / current_bpm);
                
                time += time_until_change;
                current_beat = change_beats;
                current_bpm = change.bpm;
            } else {
                break;
            }
        }
        
        let remaining_beats = target_beats - current_beat;
        time += remaining_beats * (60.0 / current_bpm);
        
        time
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_parse_malody_chart() {
        let test_json = r#"
        {
            "meta": {
                "$ver": 0,
                "creator": "Test Creator",
                "background": "bg.jpg",
                "version": "Test Version",
                "id": 12345,
                "mode": 0,
                "time": 1234567890,
                "song": {
                    "title": "Test Song",
                    "artist": "Test Artist",
                    "titleorg": "Test Song Original",
                    "artistorg": "Test Artist Original",
                    "id": 54321
                },
                "mode_ext": {
                    "column": 4,
                    "bar_begin": 0
                }
            },
            "time": [
                {"beat": [0, 0, 1], "bpm": 120.0}
            ],
            "effect": [],
            "note": [
                {"beat": [0, 0, 1], "sound": "test.ogg", "vol": 100, "offset": 0, "type": 1},
                {"beat": [4, 0, 4], "column": 0},
                {"beat": [8, 0, 4], "column": 1},
                {"beat": [12, 0, 4], "column": 2},
                {"beat": [16, 0, 4], "column": 3}
            ],
            "extra": {
                "test": {
                    "divide": 4,
                    "speed": 100,
                    "save": 0,
                    "lock": 0,
                    "edit_mode": 0
                }
            }
        }"#;
        
        let result = MalodyParser::parse_from_str(test_json);
        assert!(result.is_ok());
        
        let chart = result.unwrap();
        assert_eq!(chart.metadata.title, "Test Song");
        assert_eq!(chart.metadata.artist, "Test Artist");
        assert_eq!(chart.metadata.creator, "Test Creator");
        assert_eq!(chart.metadata.columns, 4);
        assert_eq!(chart.metadata.audio, Some("test.ogg".to_string()));
        assert_eq!(chart.notes.len(), 4); // 第一个是音频引用，不包括在notes中
    }
}