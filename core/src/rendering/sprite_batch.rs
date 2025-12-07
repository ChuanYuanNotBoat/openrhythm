use crate::rendering::{Color, Vertex};
use glam::{Vec2, Vec3, Vec4, Mat4};
use std::sync::Arc;

pub struct Sprite {
    pub position: Vec2,
    pub size: Vec2,
    pub rotation: f32,
    pub color: Color,
    pub texture_id: Option<u64>,
    pub uv_rect: (f32, f32, f32, f32), // min_x, min_y, max_x, max_y
}

impl Sprite {
    pub fn new(position: Vec2, size: Vec2) -> Self {
        Self {
            position,
            size,
            rotation: 0.0,
            color: Color::WHITE,
            texture_id: None,
            uv_rect: (0.0, 0.0, 1.0, 1.0),
        }
    }
    
    pub fn with_color(mut self, color: Color) -> Self {
        self.color = color;
        self
    }
    
    pub fn with_texture(mut self, texture_id: u64) -> Self {
        self.texture_id = Some(texture_id);
        self
    }
    
    pub fn with_uv(mut self, uv_rect: (f32, f32, f32, f32)) -> Self {
        self.uv_rect = uv_rect;
        self
    }
}

pub struct SpriteBatch {
    sprites: Vec<Sprite>,
    vertices: Vec<Vertex>,
    indices: Vec<u16>,
    needs_rebuild: bool,
}

impl SpriteBatch {
    pub fn new() -> Self {
        Self {
            sprites: Vec::new(),
            vertices: Vec::new(),
            indices: Vec::new(),
            needs_rebuild: true,
        }
    }
    
    pub fn add_sprite(&mut self, sprite: Sprite) {
        self.sprites.push(sprite);
        self.needs_rebuild = true;
    }
    
    pub fn clear(&mut self) {
        self.sprites.clear();
        self.needs_rebuild = true;
    }
    
    pub fn rebuild(&mut self) {
        self.vertices.clear();
        self.indices.clear();
        
        let mut vertex_offset = 0;
        
        for sprite in &self.sprites {
            // 计算变换矩阵
            let translation = glam::Mat4::from_translation(glam::Vec3::new(
                sprite.position.x,
                sprite.position.y,
                0.0,
            ));
            
            let rotation = glam::Mat4::from_rotation_z(sprite.rotation.to_radians());
            let scale = glam::Mat4::from_scale(glam::Vec3::new(
                sprite.size.x,
                sprite.size.y,
                1.0,
            ));
            
            let transform = translation * rotation * scale;
            
            // 定义单位正方形的四个顶点
            let corners = [
                glam::Vec3::new(-0.5, -0.5, 0.0),
                glam::Vec3::new(0.5, -0.5, 0.0),
                glam::Vec3::new(0.5, 0.5, 0.0),
                glam::Vec3::new(-0.5, 0.5, 0.0),
            ];
            
            let uv_coords = [
                glam::Vec2::new(sprite.uv_rect.0, sprite.uv_rect.3), // 左下
                glam::Vec2::new(sprite.uv_rect.2, sprite.uv_rect.3), // 右下
                glam::Vec2::new(sprite.uv_rect.2, sprite.uv_rect.1), // 右上
                glam::Vec2::new(sprite.uv_rect.0, sprite.uv_rect.1), // 左上
            ];
            
            let color = glam::Vec4::new(
                sprite.color.r,
                sprite.color.g,
                sprite.color.b,
                sprite.color.a,
            );
            
            // 添加顶点
            for i in 0..4 {
                let world_pos = transform.transform_point3(corners[i]);
                self.vertices.push(Vertex {
                    position: world_pos,
                    color,
                    tex_coord: uv_coords[i],
                });
            }
            
            // 添加索引（两个三角形组成一个矩形）
            self.indices.extend_from_slice(&[
                vertex_offset,
                vertex_offset + 1,
                vertex_offset + 2,
                vertex_offset,
                vertex_offset + 2,
                vertex_offset + 3,
            ]);
            
            vertex_offset += 4;
        }
        
        self.needs_rebuild = false;
    }
    
    pub fn vertices(&self) -> &[Vertex] {
        &self.vertices
    }
    
    pub fn indices(&self) -> &[u16] {
        &self.indices
    }
    
    pub fn sprite_count(&self) -> usize {
        self.sprites.len()
    }
    
    pub fn needs_rebuild(&self) -> bool {
        self.needs_rebuild
    }
}