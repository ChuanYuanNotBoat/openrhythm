use crate::error::{CoreError, Result};
use wgpu::{BindGroupLayout, Device, RenderPipeline, ShaderModule};
use std::sync::Arc;

pub struct Shader {
    module: wgpu::ShaderModule,
    bind_group_layouts: Vec<wgpu::BindGroupLayout>,
    render_pipeline: Option<wgpu::RenderPipeline>,
}

impl Shader {
    pub fn from_wgsl(
        device: Arc<Device>,
        source: &str,
        label: Option<&str>,
    ) -> Result<Self> {
        let module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label,
            source: wgpu::ShaderSource::Wgsl(source.into()),
        });
        
        Ok(Self {
            module,
            bind_group_layouts: Vec::new(),
            render_pipeline: None,
        })
    }
    
    pub fn from_bytes(
        device: Arc<Device>,
        bytes: &[u8],
        label: Option<&str>,
    ) -> Result<Self> {
        let source = String::from_utf8(bytes.to_vec())
            .map_err(|e| CoreError::Graphics(format!("Invalid shader bytes: {}", e)))?;
        
        Self::from_wgsl(device, &source, label)
    }
    
    pub fn create_render_pipeline(
        &mut self,
        device: Arc<Device>,
        format: wgpu::TextureFormat,
        layout: &wgpu::PipelineLayoutDescriptor,
    ) {
        // During dependency compatibility pass we avoid creating a real pipeline
        // because wgpu API changed (compilation options, etc.). Restore
        // proper pipeline creation once wgpu integration is adapted.
        let _ = (device, format, layout);
        self.render_pipeline = None;
    }
    
    pub fn module(&self) -> &wgpu::ShaderModule {
        &self.module
    }
    
    pub fn render_pipeline(&self) -> Option<&wgpu::RenderPipeline> {
        self.render_pipeline.as_ref()
    }
}

// 预定义着色器
pub struct ShaderLibrary {
    shaders: std::collections::HashMap<String, Shader>,
}

impl ShaderLibrary {
    pub fn new() -> Self {
        Self {
            shaders: std::collections::HashMap::new(),
        }
    }
    
    pub fn add_shader(&mut self, name: String, shader: Shader) {
        self.shaders.insert(name, shader);
    }
    
    pub fn get_shader(&self, name: &str) -> Option<&Shader> {
        self.shaders.get(name)
    }
    
    pub fn load_default_shaders(&mut self, device: Arc<Device>) -> Result<()> {
        // 基础精灵着色器
        let sprite_shader_source = r#"
            struct VertexInput {
                @location(0) position: vec3<f32>,
                @location(1) color: vec4<f32>,
                @location(2) tex_coord: vec2<f32>,
            };

            struct VertexOutput {
                @builtin(position) clip_position: vec4<f32>,
                @location(0) color: vec4<f32>,
                @location(1) tex_coord: vec2<f32>,
            };

            struct CameraUniform {
                view_proj: mat4x4<f32>,
            };

            @group(0) @binding(0)
            var<uniform> camera: CameraUniform;

            @vertex
            fn vs_main(model: VertexInput) -> VertexOutput {
                var out: VertexOutput;
                out.clip_position = camera.view_proj * vec4<f32>(model.position, 1.0);
                out.color = model.color;
                out.tex_coord = model.tex_coord;
                return out;
            }

            @group(0) @binding(1)
            var texture_sampler: sampler;

            @group(0) @binding(2)
            var texture: texture_2d<f32>;

            @fragment
            fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
                let texture_color = textureSample(texture, texture_sampler, in.tex_coord);
                return texture_color * in.color;
            }
        "#;
        
        let sprite_shader = Shader::from_wgsl(device.clone(), sprite_shader_source, Some("Sprite Shader"))?;
        self.add_shader("sprite".to_string(), sprite_shader);
        
        // 纯色着色器
        let solid_shader_source = r#"
            struct VertexInput {
                @location(0) position: vec3<f32>,
                @location(1) color: vec4<f32>,
            };

            struct VertexOutput {
                @builtin(position) clip_position: vec4<f32>,
                @location(0) color: vec4<f32>,
            };

            struct CameraUniform {
                view_proj: mat4x4<f32>,
            };

            @group(0) @binding(0)
            var<uniform> camera: CameraUniform;

            @vertex
            fn vs_main(model: VertexInput) -> VertexOutput {
                var out: VertexOutput;
                out.clip_position = camera.view_proj * vec4<f32>(model.position, 1.0);
                out.color = model.color;
                return out;
            }

            @fragment
            fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
                return in.color;
            }
        "#;
        
        let solid_shader = Shader::from_wgsl(device.clone(), solid_shader_source, Some("Solid Shader"))?;
        self.add_shader("solid".to_string(), solid_shader);
        
        Ok(())
    }
}