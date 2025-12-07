use crate::error::{CoreError, Result};
use wgpu::{
    Adapter, Backends, Device, DeviceDescriptor, Instance, InstanceDescriptor,
    Limits, LoadOp, Operations, Queue, RenderPassColorAttachment, RenderPassDescriptor,
    Surface, SurfaceConfiguration, SurfaceTexture, TextureUsages, TextureViewDescriptor,
    TextureFormat,
};
use winit::window::Window;
use std::sync::Arc;

pub struct RenderStats {
    pub draw_calls: u32,
    pub vertices_count: u32,
    pub textures_loaded: u32,
    pub frame_time_ms: f32,
}

pub struct Renderer {
    surface: Surface,
    device: Arc<Device>,
    queue: Arc<Queue>,
    config: SurfaceConfiguration,
    size: winit::dpi::PhysicalSize<u32>,
    window: Arc<Window>,
    
    // 统计信息
    stats: RenderStats,
    frame_counter: u64,
}

impl Renderer {
    pub async fn new(window: Arc<Window>) -> Result<Self> {
        let size = window.inner_size();
        
        // 实例 - 移除引用符号
        let instance = Instance::new(InstanceDescriptor {
            backends: Backends::all(),
            ..Default::default()
        });
        
        // 表面 - 使用正确的窗口引用
        let surface = unsafe { instance.create_surface(&window) }
            .map_err(|e| CoreError::Graphics(format!("Failed to create surface: {}", e)))?;
        
        // 适配器
        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: Some(&surface),
                force_fallback_adapter: false,
            })
            .await
            .ok_or(CoreError::Graphics("Failed to find suitable adapter".to_string()))?;
        
        // 设备和队列 - 更新 DeviceDescriptor 结构
        let (device, queue) = adapter
            .request_device(
                &DeviceDescriptor {
                    label: Some("OpenRhythm Device"),
                    features: wgpu::Features::empty(),  // 注意：required_features 改为 features
                    limits: Limits::default(),  // 注意：required_limits 改为 limits
                },
                None,
            )
            .await
            .map_err(|e| CoreError::Graphics(format!("Failed to request device: {}", e)))?;
        
        let device = Arc::new(device);
        let queue = Arc::new(queue);
        
        // 表面配置
        let surface_caps = surface.get_capabilities(&adapter);
        let surface_format = surface_caps
            .formats
            .iter()
            .copied()
            .find(|f| f.is_srgb())
            .unwrap_or(surface_caps.formats[0]);
        
        let config = SurfaceConfiguration {
            usage: TextureUsages::RENDER_ATTACHMENT,
            format: surface_format,
            width: size.width,
            height: size.height,
            present_mode: surface_caps.present_modes[0],
            alpha_mode: surface_caps.alpha_modes[0],
        };
        
        surface.configure(&*device, &config);
        
        Ok(Self {
            surface,
            device,
            queue,
            config,
            size,
            window,
            stats: RenderStats {
                draw_calls: 0,
                vertices_count: 0,
                textures_loaded: 0,
                frame_time_ms: 0.0,
            },
            frame_counter: 0,
        })
    }
    
    pub fn resize(&mut self, new_size: winit::dpi::PhysicalSize<u32>) {
        if new_size.width > 0 && new_size.height > 0 {
            self.size = new_size;
            self.config.width = new_size.width;
            self.config.height = new_size.height;
            self.surface.configure(&self.device, &self.config);
        }
    }
    
    pub fn begin_frame(&mut self) -> Result<wgpu::SurfaceTexture> {
        self.frame_counter += 1;
        
        let frame = self.surface.get_current_texture()
            .map_err(|e| CoreError::Graphics(format!("Failed to get next surface texture: {}", e)))?;
        
        Ok(frame)
    }
    
    pub fn end_frame(&self, frame: wgpu::SurfaceTexture) {
        frame.present();
    }
    
    pub fn create_command_encoder(&self) -> wgpu::CommandEncoder {
        self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("Render Command Encoder"),
        })
    }
    
    pub fn create_render_pass<'b>(
        &self,
        encoder: &'b mut wgpu::CommandEncoder,
        view: &'b wgpu::TextureView,
        clear_color: wgpu::Color,
    ) -> wgpu::RenderPass<'b> {
        encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("Render Pass"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(clear_color),
                    store: wgpu::StoreOp::Store,
                },
            })],
            depth_stencil_attachment: None,
        })
    }
    
    pub fn device(&self) -> Arc<wgpu::Device> {
        self.device.clone()
    }
    
    pub fn queue(&self) -> Arc<wgpu::Queue> {
        self.queue.clone()
    }
    
    pub fn size(&self) -> (u32, u32) {
        (self.size.width, self.size.height)
    }
    
    pub fn aspect_ratio(&self) -> f32 {
        self.size.width as f32 / self.size.height as f32
    }
    
    pub fn update_stats(&mut self, delta_time: f32) {
        self.stats.frame_time_ms = delta_time * 1000.0;
    }
    
    pub fn stats(&self) -> &RenderStats {
        &self.stats
    }
    
    pub fn reset_stats(&mut self) {
        self.stats.draw_calls = 0;
        self.stats.vertices_count = 0;
        self.stats.textures_loaded = 0;
        self.stats.frame_time_ms = 0.0;
    }
    
    pub fn present_frame(&mut self, frame: wgpu::SurfaceTexture) {
        frame.present();
    }
}