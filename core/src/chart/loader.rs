use crate::error::{CoreError, Result};
use super::{parser::MalodyParser, model::Chart};
use std::path::{Path, PathBuf};

pub struct ChartLoader;

impl ChartLoader {
    pub fn new() -> Self {
        Self
    }
    
    pub fn load_from_path<P: AsRef<Path>>(&self, path: P) -> Result<Chart> {
        let path = path.as_ref();
        
        match path.extension().and_then(|s| s.to_str()) {
            Some("mc") | Some("json") => {
                // 直接加载.mc或.json文件
                MalodyParser::parse_from_file(path)
            }
            Some("mcz") => {
                // 处理MCZ文件
                self.load_from_mcz(path)
            }
            _ => Err(CoreError::Parse(format!(
                "Unsupported chart format: {:?}", 
                path.extension()
            ))),
        }
    }
    
    pub fn load_from_mcz<P: AsRef<Path>>(&self, path: P) -> Result<Chart> {
        // MCZ文件应该包含多个谱面，这里先加载第一个
        let charts = self.extract_mcz_charts(path)?;
        
        charts.into_iter().next()
            .ok_or_else(|| CoreError::Parse("No charts found in MCZ file".to_string()))
    }
    
    pub fn extract_mcz_charts<P: AsRef<Path>>(&self, path: P) -> Result<Vec<Chart>> {
        let file = std::fs::File::open(path.as_ref())?;
        let mut archive = zip::ZipArchive::new(file)?;
        
        let mut charts = Vec::new();
        
        for i in 0..archive.len() {
            let mut file = archive.by_index(i)?;
            
            if file.name().ends_with(".mc") {
                let mut content = String::new();
                std::io::Read::read_to_string(&mut file, &mut content)?;
                
                match MalodyParser::parse_from_str(&content) {
                    Ok(chart) => charts.push(chart),
                    Err(e) => {
                        log::warn!("Failed to parse chart in MCZ: {}", e);
                        continue;
                    }
                }
            }
        }
        
        Ok(charts)
    }
    
    pub fn load_chart_with_resources<P: AsRef<Path>>(&self, path: P) -> Result<ChartWithResources> {
        let chart = self.load_from_path(path)?;
        let resources = self.extract_chart_resources(&chart)?;
        
        Ok(ChartWithResources { chart, resources })
    }
    
    fn extract_chart_resources(&self, chart: &Chart) -> Result<Vec<ChartResource>> {
        let mut resources = Vec::new();
        
        // 提取音频文件信息
        if let Some(audio_path) = &chart.metadata.audio {
            resources.push(ChartResource {
                path: audio_path.clone(),
                resource_type: ChartResourceType::Audio,
            });
        }
        
        // 提取背景图片信息
        if let Some(bg_path) = &chart.metadata.background {
            resources.push(ChartResource {
                path: bg_path.clone(),
                resource_type: ChartResourceType::Background,
            });
        }
        
        // 提取音效文件（从自定义数据中）
        if let Some(audio_files) = chart.custom_data.get("audio_files") {
            if let Some(files) = audio_files.as_object() {
                for (_, value) in files {
                    if let Some(path) = value.as_str() {
                        resources.push(ChartResource {
                            path: path.to_string(),
                            resource_type: ChartResourceType::SoundEffect,
                        });
                    }
                }
            }
        }
        
        Ok(resources)
    }
}

#[derive(Debug, Clone)]
pub struct ChartWithResources {
    pub chart: Chart,
    pub resources: Vec<ChartResource>,
}

#[derive(Debug, Clone)]
pub struct ChartResource {
    pub path: String,
    pub resource_type: ChartResourceType,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChartResourceType {
    Audio,
    Background,
    SoundEffect,
    Other,
}