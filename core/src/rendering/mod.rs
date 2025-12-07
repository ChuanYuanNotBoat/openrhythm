mod renderer;
mod texture;
mod shader;
mod sprite_batch;
mod ui_renderer;

pub use renderer::*;
pub use texture::*;
pub use shader::*;
pub use sprite_batch::*;
pub use ui_renderer::*;

// 公共类型
use glam::{Vec2, Vec3, Vec4, Mat4};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Color {
    pub r: f32,
    pub g: f32,
    pub b: f32,
    pub a: f32,
}

impl Color {
    pub const WHITE: Self = Self { r: 1.0, g: 1.0, b: 1.0, a: 1.0 };
    pub const BLACK: Self = Self { r: 0.0, g: 0.0, b: 0.0, a: 1.0 };
    pub const RED: Self = Self { r: 1.0, g: 0.0, b: 0.0, a: 1.0 };
    pub const GREEN: Self = Self { r: 0.0, g: 1.0, b: 0.0, a: 1.0 };
    pub const BLUE: Self = Self { r: 0.0, g: 0.0, b: 1.0, a: 1.0 };
    pub const TRANSPARENT: Self = Self { r: 0.0, g: 0.0, b: 0.0, a: 0.0 };
    
    pub fn rgba(r: f32, g: f32, b: f32, a: f32) -> Self {
        Self { r, g, b, a }
    }
    
    pub fn rgb(r: f32, g: f32, b: f32) -> Self {
        Self { r, g, b, a: 1.0 }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct Vertex {
    pub position: Vec3,
    pub color: Vec4,
    pub tex_coord: Vec2,
}

#[derive(Debug, Clone)]
pub struct RenderStats {
    pub draw_calls: usize,
    pub vertices_count: usize,
    pub textures_loaded: usize,
    pub frame_time_ms: f32,
}

#[derive(Debug, Clone, Copy)]
pub enum BlendMode {
    Alpha,
    Additive,
    Multiply,
    Screen,
}