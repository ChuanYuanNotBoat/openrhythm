use crate::rendering::{Color, SpriteBatch, Sprite};
use glam::Vec2;

pub struct UIRenderer {
    sprite_batch: SpriteBatch,
    screen_size: (u32, u32),
}

impl UIRenderer {
    pub fn new(screen_size: (u32, u32)) -> Self {
        Self {
            sprite_batch: SpriteBatch::new(),
            screen_size,
        }
    }
    
    pub fn draw_rect(&mut self, position: Vec2, size: Vec2, color: Color) {
        let sprite = Sprite::new(position, size).with_color(color);
        self.sprite_batch.add_sprite(sprite);
    }
    
    pub fn draw_texture(&mut self, position: Vec2, size: Vec2, texture_id: u64) {
        let sprite = Sprite::new(position, size).with_texture(texture_id);
        self.sprite_batch.add_sprite(sprite);
    }
    
    pub fn draw_texture_uv(&mut self, position: Vec2, size: Vec2, texture_id: u64, uv_rect: (f32, f32, f32, f32)) {
        let sprite = Sprite::new(position, size)
            .with_texture(texture_id)
            .with_uv(uv_rect);
        self.sprite_batch.add_sprite(sprite);
    }
    
    pub fn draw_border(&mut self, position: Vec2, size: Vec2, thickness: f32, color: Color) {
        let half_thickness = thickness * 0.5;
        
        // 上边框
        self.draw_rect(
            Vec2::new(position.x, position.y - half_thickness),
            Vec2::new(size.x, thickness),
            color,
        );
        
        // 下边框
        self.draw_rect(
            Vec2::new(position.x, position.y + size.y - half_thickness),
            Vec2::new(size.x, thickness),
            color,
        );
        
        // 左边框
        self.draw_rect(
            Vec2::new(position.x - half_thickness, position.y),
            Vec2::new(thickness, size.y),
            color,
        );
        
        // 右边框
        self.draw_rect(
            Vec2::new(position.x + size.x - half_thickness, position.y),
            Vec2::new(thickness, size.y),
            color,
        );
    }
    
    pub fn draw_progress_bar(&mut self, position: Vec2, size: Vec2, progress: f32, bg_color: Color, fg_color: Color) {
        // 背景
        self.draw_rect(position, size, bg_color);
        
        // 前景（进度）
        let progress_width = size.x * progress.max(0.0).min(1.0);
        self.draw_rect(position, Vec2::new(progress_width, size.y), fg_color);
        
        // 边框
        self.draw_border(position, size, 2.0, Color::BLACK);
    }
    
    pub fn clear(&mut self) {
        self.sprite_batch.clear();
    }
    
    pub fn sprite_batch(&mut self) -> &mut SpriteBatch {
        &mut self.sprite_batch
    }
    
    pub fn set_screen_size(&mut self, size: (u32, u32)) {
        self.screen_size = size;
    }
    
    pub fn screen_to_ui(&self, screen_pos: (f32, f32)) -> Vec2 {
        let (screen_x, screen_y) = screen_pos;
        let (width, height) = self.screen_size;
        
        // 将屏幕坐标转换到UI坐标（中心为原点，Y向上）
        Vec2::new(
            (screen_x / width as f32 - 0.5) * 2.0,
            -(screen_y / height as f32 - 0.5) * 2.0,
        )
    }
}