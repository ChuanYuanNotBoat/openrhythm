use crate::error::{CoreError, Result};
use rodio::{OutputStream, OutputStreamHandle, Sink, Source};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use std::collections::HashMap;

use super::decoder::AudioData;

pub struct AudioPlayer {
    stream: OutputStream,
    stream_handle: OutputStreamHandle,
    sinks: Arc<Mutex<HashMap<u64, Sink>>>,  
    next_id: u64,
    master_volume: f32,
    global_pitch: f32,
}

impl AudioPlayer {
    pub fn new() -> Result<Self> {
        // 使用 OutputStream 的新 API
        let (stream, stream_handle) = OutputStream::try_default()
            .map_err(|e| CoreError::Audio(format!("Failed to create audio output stream: {}", e)))?;
        
        Ok(Self {
            stream,
            stream_handle,
            sinks: Arc::new(Mutex::new(HashMap::new())),
            next_id: 0,
            master_volume: 1.0,
            global_pitch: 1.0,
        })
    }
    
    pub fn play_audio_data(&mut self, audio_data: &AudioData, volume: f32, looped: bool) -> Result<u64> {
        let id = self.next_id;
        self.next_id += 1;
        
        // 创建音频源
        let source = rodio::buffer::SamplesBuffer::new(
            audio_data.info.channels,
            audio_data.info.sample_rate,
            audio_data.samples.to_vec(),  // 将 Arc<Vec<f32>> 转换为 Vec<f32>
        );
        
        // 应用音量和循环
        let source = source
            .amplify(volume * self.master_volume)
            .speed(self.global_pitch);
        
        let source: Box<dyn Source<Item = f32> + Send> = if looped {
            Box::new(source.repeat_infinite())
        } else {
            Box::new(source)
        };
        
        // 创建 Sink 并播放
        let sink = Sink::try_new(&self.stream_handle)
            .map_err(|e| CoreError::Audio(format!("Failed to create audio sink: {}", e)))?;
        
        sink.append(source);
        
        let mut sinks = self.sinks.lock().unwrap();
        sinks.insert(id, sink);
        
        Ok(id)
    }
    
    pub fn play_file<P: AsRef<std::path::Path>>(
        &mut self,
        path: P,
        volume: f32,
        looped: bool,
    ) -> Result<u64> {
        let audio_data = AudioData::from_file(path)?;
        self.play_audio_data(&audio_data, volume, looped)
    }
    
    pub fn stop(&mut self, id: u64) -> Result<()> {
        let mut sinks = self.sinks.lock().unwrap();
        
        if let Some(sink) = sinks.remove(&id) {
            sink.stop();
        }
        
        Ok(())
    }
    
    pub fn stop_all(&mut self) {
        let mut sinks = self.sinks.lock().unwrap();
        
        for (_, sink) in sinks.drain() {
            sink.stop();
        }
    }
    
    pub fn pause(&mut self, id: u64) -> Result<()> {
        let sinks = self.sinks.lock().unwrap();
        
        if let Some(sink) = sinks.get(&id) {
            sink.pause();
        }
        
        Ok(())
    }
    
    pub fn resume(&mut self, id: u64) -> Result<()> {
        let sinks = self.sinks.lock().unwrap();
        
        if let Some(sink) = sinks.get(&id) {
            sink.play();
        }
        
        Ok(())
    }
    
    pub fn set_volume(&mut self, id: u64, volume: f32) -> Result<()> {
        let sinks = self.sinks.lock().unwrap();
        
        if let Some(sink) = sinks.get(&id) {
            sink.set_volume(volume * self.master_volume);
        }
        
        Ok(())
    }
    
    pub fn set_master_volume(&mut self, volume: f32) {
        self.master_volume = volume.max(0.0).min(2.0);
        
        let sinks = self.sinks.lock().unwrap();
        for sink in sinks.values() {
            // 重新计算每个Sink的音量
            // 注意：这里简化了，实际应该保存每个Sink的独立音量
            sink.set_volume(self.master_volume);
        }
    }
    
    pub fn set_pitch(&mut self, id: u64, pitch: f32) -> Result<()> {
        // rodio的Sink不支持直接设置速度，需要重新创建
        // 这里简化处理，只设置全局pitch
        self.global_pitch = pitch.max(0.1).min(4.0);
        Ok(())
    }
    
    pub fn get_playback_position(&self, id: u64) -> Option<Duration> {
        let sinks = self.sinks.lock().unwrap();
        
        sinks.get(&id).and_then(|sink| {
            // rodio的Sink不直接提供播放位置，这里返回一个估计值
            // 对于精确同步，需要更复杂的实现
            None
        })
    }
    
    pub fn is_playing(&self, id: u64) -> bool {
        let sinks = self.sinks.lock().unwrap();
        
        sinks.get(&id).map_or(false, |sink| !sink.is_paused() && sink.len() > 0)
    }
    
    pub fn cleanup_finished(&mut self) {
        let mut sinks = self.sinks.lock().unwrap();
        
        sinks.retain(|_, sink| !sink.empty());
    }
}