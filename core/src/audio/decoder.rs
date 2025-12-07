use crate::error::{CoreError, Result};
use symphonia::core::{
    audio::{AudioBufferRef, Signal},
    codecs::{DecoderOptions, CODEC_TYPE_NULL},
    formats::FormatOptions,
    io::MediaSourceStream,
    meta::MetadataOptions,
    probe::Hint,
};
use std::fs::File;
use std::path::Path;
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct AudioInfo {
    pub sample_rate: u32,
    pub channels: u16,
    pub duration_seconds: f64,
    pub total_samples: u64,
    pub format: String,
}

#[derive(Clone)]
pub struct AudioData {
    pub samples: Arc<Vec<f32>>,
    pub info: AudioInfo,
}

impl AudioData {
    pub fn new(samples: Vec<f32>, info: AudioInfo) -> Self {
        Self {
            samples: Arc::new(samples),
            info,
        }
    }
    
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let file = File::open(path.as_ref())
            .map_err(|e| CoreError::Audio(format!("Failed to open audio file: {}", e)))?;
        
        let mss = MediaSourceStream::new(Box::new(file), Default::default());
        
        let mut hint = Hint::new();
        if let Some(ext) = path.as_ref().extension().and_then(|s| s.to_str()) {
            hint.with_extension(ext);
        }
        
        let format_opts = FormatOptions::default();
        let metadata_opts = MetadataOptions::default();
        let decoder_opts = DecoderOptions::default();
        
        let probed = symphonia::default::get_probe()
            .format(&hint, mss, &format_opts, &metadata_opts)
            .map_err(|e| CoreError::Audio(format!("Failed to probe audio format: {}", e)))?;
        
        let mut format = probed.format;
        let track = format
            .tracks()
            .iter()
            .find(|t| t.codec_params.codec != CODEC_TYPE_NULL)
            .ok_or_else(|| CoreError::Audio("No supported audio tracks found".to_string()))?;
        
        let mut decoder = symphonia::default::get_codecs()
            .make(&track.codec_params, &decoder_opts)
            .map_err(|e| CoreError::Audio(format!("Failed to create decoder: {}", e)))?;
        
        let track_id = track.id;
        
        let mut samples = Vec::new();
        let mut sample_rate = 0;
        let mut channels = 0;
        let mut total_samples = 0;
        
        while let Ok(packet) = format.next_packet() {
            if packet.track_id() != track_id {
                continue;
            }
            
            match decoder.decode(&packet) {
                Ok(decoded) => {
                    match decoded {
                        AudioBufferRef::F32(buf) => {
                            sample_rate = buf.spec().rate;
                            channels = buf.spec().channels.count() as u16;
                            total_samples += buf.frames() as u64;
                            
                            for ch in 0..buf.spec().channels.count() {
                                let ch_samples = buf.chan(ch);
                                for &sample in ch_samples {
                                    samples.push(sample);
                                }
                            }
                        }
                        AudioBufferRef::S16(buf) => {
                            sample_rate = buf.spec().rate;
                            channels = buf.spec().channels.count() as u16;
                            total_samples += buf.frames() as u64;
                            
                            for ch in 0..buf.spec().channels.count() {
                                let ch_samples = buf.chan(ch);
                                for &sample in ch_samples {
                                    samples.push(sample as f32 / 32768.0);
                                }
                            }
                        }
                        AudioBufferRef::S24(buf) => {
                            sample_rate = buf.spec().rate;
                            channels = buf.spec().channels.count() as u16;
                            total_samples += buf.frames() as u64;
                            
                            for ch in 0..buf.spec().channels.count() {
                                let ch_samples = buf.chan(ch);
                                for sample in ch_samples {
                                    // 使用 i24 的 bits() 方法获取原始比特值，然后转换为 i32
                                    let bits = sample.bits();
                                    // 将 24 位有符号整数转换为 32 位
                                    // 如果第 23 位是 1（负数），则进行符号扩展
                                    let val = if (bits >> 23) & 1 == 1 {
                                        bits as i32 | 0xFF00_0000 // 符号扩展
                                    } else {
                                        bits as i32
                                    };
                                    samples.push(val as f32 / 8388608.0);
                                }
                            }
                        }
                        AudioBufferRef::S32(buf) => {
                            sample_rate = buf.spec().rate;
                            channels = buf.spec().channels.count() as u16;
                            total_samples += buf.frames() as u64;
                            
                            for ch in 0..buf.spec().channels.count() {
                                let ch_samples = buf.chan(ch);
                                for &sample in ch_samples {
                                    samples.push(sample as f32 / 2147483648.0);
                                }
                            }
                        }
                        AudioBufferRef::U8(buf) => {
                            sample_rate = buf.spec().rate;
                            channels = buf.spec().channels.count() as u16;
                            total_samples += buf.frames() as u64;
                            
                            for ch in 0..buf.spec().channels.count() {
                                let ch_samples = buf.chan(ch);
                                for &sample in ch_samples {
                                    samples.push((sample as f32 - 128.0) / 128.0);
                                }
                            }
                        }
                        _ => {
                            return Err(CoreError::Audio("Unsupported audio format".to_string()));
                        }
                    }
                }
                Err(e) => {
                    log::warn!("Error decoding audio packet: {}", e);
                    break;
                }
            }
        }
        
        let duration_seconds = if sample_rate > 0 && channels > 0 {
            total_samples as f64 / (sample_rate as f64 * channels as f64)
        } else {
            0.0
        };
        
        let info = AudioInfo {
            sample_rate,
            channels,
            duration_seconds,
            total_samples,
            format: "audio".to_string(),
        };
        
        Ok(Self::new(samples, info))
    }
    
    pub fn resample(&self, target_sample_rate: u32) -> Result<Self> {
        if self.info.sample_rate == target_sample_rate {
            return Ok(self.clone());
        }
        
        use rubato::{
            Resampler, SincFixedIn, SincInterpolationParameters, SincInterpolationType,
            WindowFunction,
        };
        
        let channels = self.info.channels as usize;
        let input_rate = self.info.sample_rate as f64;
        let output_rate = target_sample_rate as f64;
        let ratio = output_rate / input_rate;
        
        let frames = self.samples.len() / channels;
        
        // 准备输入数据
        let mut input_vec = Vec::new();
        for channel in 0..channels {
            let mut channel_data = Vec::new();
            for i in 0..frames {
                channel_data.push(self.samples[i * channels + channel]);
            }
            input_vec.push(channel_data);
        }
        
        // 创建重采样器
        let params = SincInterpolationParameters {
            sinc_len: 256,
            f_cutoff: 0.95,
            interpolation: SincInterpolationType::Linear,
            oversampling_factor: 256,
            window: WindowFunction::BlackmanHarris2,
        };
        
        let mut resampler = SincFixedIn::new(
            ratio,
            2.0,
            params,
            frames,
            channels,
        ).map_err(|e| CoreError::Audio(format!("Failed to create resampler: {}", e)))?;
        
        // 执行重采样
        let output_vec = resampler
            .process(&input_vec, None)
            .map_err(|e| CoreError::Audio(format!("Failed to resample audio: {}", e)))?;
        
        // 合并通道
        let output_frames = output_vec[0].len();
        let mut output_samples = Vec::with_capacity(output_frames * channels);
        
        for i in 0..output_frames {
            for channel in 0..channels {
                output_samples.push(output_vec[channel][i]);
            }
        }
        
        let total_samples = output_frames as u64 * channels as u64;
        let duration_seconds = total_samples as f64 / (target_sample_rate * channels as u32) as f64;
        
        let info = AudioInfo {
            sample_rate: target_sample_rate,
            channels: self.info.channels,
            duration_seconds,
            total_samples,
            format: self.info.format.clone(),
        };
        
        Ok(Self::new(output_samples, info))
    }
    
    pub fn normalize(&mut self) {
        if self.samples.is_empty() {
            return;
        }
        
        // 计算最大值
        let max_abs: f32 = self
            .samples
            .iter()
            .fold(0.0_f32, |max, &sample| max.max(sample.abs()));
        
        if max_abs > 0.0 && max_abs < 1.0 {
            // 如果最大值小于1，进行归一化
            let scale = 0.95 / max_abs; // 留出5%余量避免削波
            let samples: Vec<f32> = self.samples.iter().map(|&s| s * scale).collect();
            self.samples = Arc::new(samples);
        }
    }
    
    pub fn trim_silence(&mut self, threshold: f32) {
        if self.samples.is_empty() {
            return;
        }
        
        let channels = self.info.channels as usize;
        let frames = self.samples.len() / channels;
        
        // 找到第一个超过阈值的帧
        let mut start_frame = 0;
        for i in 0..frames {
            let mut frame_energy = 0.0;
            for ch in 0..channels {
                let sample = self.samples[i * channels + ch];
                frame_energy += sample.abs();
            }
            frame_energy /= channels as f32;
            
            if frame_energy > threshold {
                start_frame = i;
                break;
            }
        }
        
        // 找到最后一个超过阈值的帧
        let mut end_frame = frames - 1;
        for i in (0..frames).rev() {
            let mut frame_energy = 0.0;
            for ch in 0..channels {
                let sample = self.samples[i * channels + ch];
                frame_energy += sample.abs();
            }
            frame_energy /= channels as f32;
            
            if frame_energy > threshold {
                end_frame = i;
                break;
            }
        }
        
        if start_frame >= end_frame {
            return;
        }
        
        // 提取非静音部分
        let new_frames = end_frame - start_frame + 1;
        let mut new_samples = Vec::with_capacity(new_frames * channels);
        
        for i in start_frame..=end_frame {
            for ch in 0..channels {
                new_samples.push(self.samples[i * channels + ch]);
            }
        }
        
        self.samples = Arc::new(new_samples);
        self.info.total_samples = new_frames as u64 * channels as u64;
        self.info.duration_seconds = self.info.total_samples as f64
            / (self.info.sample_rate * channels as u32) as f64;
    }
}