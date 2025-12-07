use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, SampleFormat, StreamConfig, SupportedStreamConfig};
use rubato::{Resampler, SincFixedIn, WindowFunction, SincInterpolationType};  // 添加 SincInterpolationType
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use crate::error::Result;

pub struct AudioEngine {
    host: cpal::Host,
    device: Device,
    config: StreamConfig,
    sample_format: SampleFormat,
    
    streams: Arc<Mutex<HashMap<u64, AudioStream>>>,
    next_stream_id: u64,
    
    sample_rate: u32,
    channels: u16,
}

pub struct AudioStream {
    pub data: Vec<f32>,
    pub position: usize,
    pub volume: f32,
    pub looped: bool,
    pub playing: bool,
}

impl AudioEngine {
    pub fn new() -> Result<Self> {
        let host = cpal::default_host();
        let device = host.default_output_device()
            .ok_or_else(|| crate::error::CoreError::Audio("No audio output device found".to_string()))?;
        
        let supported_config = device.default_output_config()?;
        
        let config = StreamConfig {
            channels: supported_config.channels(),
            sample_rate: supported_config.sample_rate(),
            buffer_size: cpal::BufferSize::Default,
        };
        
        Ok(Self {
            host,
            device,
            config: config.clone(),
            sample_format: supported_config.sample_format(),
            
            streams: Arc::new(Mutex::new(HashMap::new())),
            next_stream_id: 0,
            
            sample_rate: config.sample_rate.0,
            channels: config.channels,
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
            _ => return Err(crate::error::CoreError::Audio(
                format!("Unsupported sample format: {:?}", self.sample_format)
            )),
        };
        
        stream.play()?;
        
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
            if !stream.playing {
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
    
    pub fn play(
        &mut self,
        data: Vec<f32>,
        sample_rate: u32,
        volume: f32,
        looped: bool,
    ) -> Result<u64> {
        let mut streams = self.streams.lock().unwrap();
        
        let stream_id = self.next_stream_id;
        self.next_stream_id += 1;
        
        // 如果需要，重新采样音频
        let resampled_data = if sample_rate != self.sample_rate {
            self.resample_audio(&data, sample_rate, self.sample_rate)?
        } else {
            data
        };
        
        streams.insert(stream_id, AudioStream {
            data: resampled_data,
            position: 0,
            volume,
            looped,
            playing: true,
        });
        
        Ok(stream_id)
    }
    
    fn resample_audio(
        &self,
        input: &[f32],
        input_rate: u32,
        output_rate: u32,
    ) -> Result<Vec<f32>> {
        let channels = 1; // 单声道
        
        let resampler = SincFixedIn::new(
            output_rate as f64 / input_rate as f64,
            2.0,
            rubato::SincInterpolationParameters {
                sinc_len: 256,
                f_cutoff: 0.95,
                window: WindowFunction::BlackmanHarris2,
                oversampling_factor: 256,
                interpolation: SincInterpolationType::Linear,  // 修复这里
            },
            input.len() / channels,
            channels,
        ).map_err(|e| crate::error::CoreError::Audio(format!("Resampler error: {}", e)))?;
        
        let input_vec = vec![input.to_vec()];
        let output_vec = resampler.process(&input_vec, None)
            .map_err(|e| crate::error::CoreError::Audio(format!("Resampling error: {}", e)))?;
        
        Ok(output_vec[0].clone())
    }
    
    pub fn stop(&mut self, stream_id: u64) -> Result<()> {
        let mut streams = self.streams.lock().unwrap();
        
        if let Some(stream) = streams.get_mut(&stream_id) {
            stream.playing = false;
        }
        
        Ok(())
    }
    
    pub fn set_volume(&mut self, stream_id: u64, volume: f32) -> Result<()> {
        let mut streams = self.streams.lock().unwrap();
        
        if let Some(stream) = streams.get_mut(&stream_id) {
            stream.volume = volume.max(0.0).min(1.0);
        }
        
        Ok(())
    }
}