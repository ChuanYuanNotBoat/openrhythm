use crate::error::{CoreError, Result};
use cpal::{
    traits::{DeviceTrait, HostTrait, StreamTrait},
    Device, SampleFormat, StreamConfig, SupportedStreamConfig,
};
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

use super::decoder::AudioData;

pub struct LowLatencyAudioEngine {
    device: Device,
    config: StreamConfig,
    sample_format: SampleFormat,
    
    streams: Arc<Mutex<HashMap<u64, AudioStream>>>,
    next_stream_id: u64,
    
    sample_rate: u32,
    channels: u16,
    stream_handle: Option<cpal::Stream>,
}

struct AudioStream {
    data: Arc<Vec<f32>>,
    position: usize,
    volume: f32,
    looped: bool,
    playing: bool,
    paused: bool,
}

impl LowLatencyAudioEngine {
    pub fn new(target_latency_ms: u32) -> Result<Self> {
        let host = cpal::default_host();
        let device = host.default_output_device()
            .ok_or_else(|| CoreError::Audio("No audio output device found".to_string()))?;
        
        let supported_config = device.default_output_config()?;
        
        // 计算缓冲区大小以达到目标延迟
        let sample_rate = supported_config.sample_rate().0;
        let buffer_size = (sample_rate as f32 * target_latency_ms as f32 / 1000.0) as u32;
        
        let config = StreamConfig {
            channels: supported_config.channels(),
            sample_rate: supported_config.sample_rate(),
            buffer_size: cpal::BufferSize::Fixed(buffer_size.max(256)),
        };
        
        Ok(Self {
            device,
            config: config.clone(),
            sample_format: supported_config.sample_format(),
            
            streams: Arc::new(Mutex::new(HashMap::new())),
            next_stream_id: 0,
            
            sample_rate: config.sample_rate.0,
            channels: config.channels,
            stream_handle: None,
        })
    }
    
    pub fn start(&mut self) -> Result<()> {
        let channels = self.config.channels;
        let sample_rate = self.config.sample_rate.0;
        let streams = self.streams.clone();
        
        let err_fn = |err| {
            log::error!("Audio stream error: {}", err);
        };
        
        let stream = match self.sample_format {
            SampleFormat::F32 => self.device.build_output_stream(
                &self.config,
                move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                    Self::audio_callback(data, channels as usize, sample_rate, &streams);
                },
                err_fn,
                None,
            )?,
            _ => return Err(CoreError::Audio(
                format!("Unsupported sample format: {:?}", self.sample_format)
            )),
        };
        
        stream.play()?;
        self.stream_handle = Some(stream);
        
        Ok(())
    }
    
    fn audio_callback(
        output: &mut [f32],
        channels: usize,
        sample_rate: u32,
        streams: &Arc<Mutex<HashMap<u64, AudioStream>>>,
    ) {
        let mut streams_guard = streams.lock().unwrap();
        
        // 清零输出缓冲区
        for sample in output.iter_mut() {
            *sample = 0.0;
        }
        
        // 混合所有音频流
        for stream in streams_guard.values_mut() {
            if !stream.playing || stream.paused {
                continue;
            }
            
            let mut sample_index = 0;
            while sample_index < output.len() && stream.position < stream.data.len() {
                let audio_sample = stream.data[stream.position] * stream.volume;
                
                // 立体声混合
                for channel in 0..channels {
                    let output_index = sample_index + channel;
                    if output_index < output.len() {
                        output[output_index] += audio_sample;
                    }
                }
                
                stream.position += 1;
                sample_index += channels;
                
                // 循环处理
                if stream.position >= stream.data.len() {
                    if stream.looped {
                        stream.position = 0;
                    } else {
                        stream.playing = false;
                        break;
                    }
                }
            }
        }
        
        // 移除已停止的流
        streams_guard.retain(|_, stream| stream.playing || stream.looped);
    }
    
    pub fn play_audio_data(&mut self, audio_data: &AudioData, volume: f32, looped: bool) -> Result<u64> {
        let mut streams = self.streams.lock().unwrap();
        
        let stream_id = self.next_stream_id;
        self.next_stream_id += 1;
        
        // 如果需要，重新采样音频
        let samples_vec = if audio_data.info.sample_rate != self.sample_rate {
            let resampled = audio_data.resample(self.sample_rate)?;
            resampled.samples.as_ref().clone()
        } else {
            audio_data.samples.as_ref().clone()
        };

        streams.insert(stream_id, AudioStream {
            data: Arc::new(samples_vec),
            position: 0,
            volume: volume.max(0.0).min(2.0),
            looped,
            playing: true,
            paused: false,
        });
        
        Ok(stream_id)
    }
    
    pub fn stop(&mut self, stream_id: u64) -> Result<()> {
        let mut streams = self.streams.lock().unwrap();
        
        if let Some(stream) = streams.get_mut(&stream_id) {
            stream.playing = false;
        }
        
        Ok(())
    }
    
    pub fn pause(&mut self, stream_id: u64) -> Result<()> {
        let mut streams = self.streams.lock().unwrap();
        
        if let Some(stream) = streams.get_mut(&stream_id) {
            stream.paused = true;
        }
        
        Ok(())
    }
    
    pub fn resume(&mut self, stream_id: u64) -> Result<()> {
        let mut streams = self.streams.lock().unwrap();
        
        if let Some(stream) = streams.get_mut(&stream_id) {
            stream.paused = false;
        }
        
        Ok(())
    }
    
    pub fn set_volume(&mut self, stream_id: u64, volume: f32) -> Result<()> {
        let mut streams = self.streams.lock().unwrap();
        
        if let Some(stream) = streams.get_mut(&stream_id) {
            stream.volume = volume.max(0.0).min(2.0);
        }
        
        Ok(())
    }
    
    pub fn get_latency_ms(&self) -> f32 {
        let buffer_samples = match self.config.buffer_size {
            cpal::BufferSize::Fixed(size) => size as f32,
            cpal::BufferSize::Default => 1024.0, // 默认值
        };
        
        buffer_samples * 1000.0 / self.sample_rate as f32
    }
    
    pub fn shutdown(&mut self) {
        self.stream_handle = None;
    }
}