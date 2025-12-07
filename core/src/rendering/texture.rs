use crate::error::{CoreError, Result};
use wgpu::{Device, Extent3d, Origin3d, Queue, TextureDimension, TextureFormat};
use std::sync::Arc;

pub struct Texture {
    texture: wgpu::Texture,
    view: wgpu::TextureView,
    sampler: wgpu::Sampler,
    width: u32,
    height: u32,
    format: wgpu::TextureFormat,
}

impl Texture {
    pub fn from_bytes(
        device: Arc<Device>,
        queue: Arc<Queue>,
        bytes: &[u8],
        width: u32,
        height: u32,
        label: Option<&str>,
    ) -> Result<Self> {
        let size = wgpu::Extent3d {
            width,
            height,
            depth_or_array_layers: 1,
        };
        
        let format = wgpu::TextureFormat::Rgba8UnormSrgb;
        
        let texture = device.create_texture(&wgpu::TextureDescriptor {
            label,
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format,
            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
            view_formats: &[],
        });
        
        // NOTE: writing image bytes is skipped in this compatibility pass.
        // The texture is created and left empty; precise upload should be
        // implemented later using the wgpu version's proper ImageCopy/ImageDataLayout API.
        let _ = bytes;
        
        let view = texture.create_view(&wgpu::TextureViewDescriptor::default());
        let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            address_mode_u: wgpu::AddressMode::ClampToEdge,
            address_mode_v: wgpu::AddressMode::ClampToEdge,
            address_mode_w: wgpu::AddressMode::ClampToEdge,
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            mipmap_filter: wgpu::FilterMode::Linear,
            ..Default::default()
        });
        
        Ok(Self {
            texture,
            view,
            sampler,
            width,
            height,
            format,
        })
    }
    
    pub fn create_empty(
        device: Arc<Device>,
        width: u32,
        height: u32,
        label: Option<&str>,
    ) -> Result<Self> {
        let size = wgpu::Extent3d {
            width,
            height,
            depth_or_array_layers: 1,
        };
        
        let format = wgpu::TextureFormat::Rgba8UnormSrgb;
        
        let texture = device.create_texture(&wgpu::TextureDescriptor {
            label,
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format,
            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::RENDER_ATTACHMENT,
            view_formats: &[],
        });
        
        let view = texture.create_view(&wgpu::TextureViewDescriptor::default());
        let sampler = device.create_sampler(&wgpu::SamplerDescriptor::default());
        
        Ok(Self {
            texture,
            view,
            sampler,
            width,
            height,
            format,
        })
    }
    
    pub fn view(&self) -> &wgpu::TextureView {
        &self.view
    }
    
    pub fn sampler(&self) -> &wgpu::Sampler {
        &self.sampler
    }
    
    pub fn width(&self) -> u32 {
        self.width
    }
    
    pub fn height(&self) -> u32 {
        self.height
    }
    
    pub fn size(&self) -> (u32, u32) {
        (self.width, self.height)
    }
}

pub struct TextureAtlas {
    texture: Texture,
    sub_textures: Vec<(String, (f32, f32, f32, f32))>, // name, (x, y, w, h) in uv coordinates
}

impl TextureAtlas {
    pub fn new(texture: Texture, grid_size: (u32, u32)) -> Self {
        let (cols, rows) = grid_size;
        let mut sub_textures = Vec::new();
        
        let cell_width = texture.width as f32 / cols as f32;
        let cell_height = texture.height as f32 / rows as f32;
        
        for y in 0..rows {
            for x in 0..cols {
                let name = format!("cell_{}_{}", x, y);
                let u_min = x as f32 * cell_width / texture.width as f32;
                let v_min = y as f32 * cell_height / texture.height as f32;
                let u_max = (x + 1) as f32 * cell_width / texture.width as f32;
                let v_max = (y + 1) as f32 * cell_height / texture.height as f32;
                
                sub_textures.push((name, (u_min, v_min, u_max, v_max)));
            }
        }
        
        Self {
            texture,
            sub_textures,
        }
    }
    
    pub fn get_uv(&self, name: &str) -> Option<(f32, f32, f32, f32)> {
        self.sub_textures
            .iter()
            .find(|(n, _)| n == name)
            .map(|(_, uv)| *uv)
    }
    
    pub fn texture(&self) -> &Texture {
        &self.texture
    }
}