mod keyboard;
mod mouse;
mod touch;
mod gamepad;
mod service;

pub use keyboard::*;
pub use mouse::*;
pub use touch::*;
pub use gamepad::*;
pub use service::*;

use crate::event::{KeyCode, KeyEvent, KeyState};

// 输入状态
#[derive(Debug, Clone, Default)]
pub struct InputState {
    pub keyboard: KeyboardState,
    pub mouse: MouseState,
    pub touches: Vec<Touch>,
    pub gamepads: Vec<GamepadState>,
}

impl InputState {
    pub fn new() -> Self {
        Self::default()
    }
    
    pub fn update(&mut self) {
        // 重置瞬时状态（如按键刚刚按下）
        self.keyboard.update();
        self.mouse.update();
    }
    
    pub fn is_key_down(&self, key: KeyCode) -> bool {
        self.keyboard.is_key_down(key)
    }
    
    pub fn is_key_pressed(&self, key: KeyCode) -> bool {
        self.keyboard.is_key_pressed(key)
    }
    
    pub fn get_mouse_position(&self) -> (f32, f32) {
        self.mouse.position
    }
    
    pub fn get_touches(&self) -> &[Touch] {
        &self.touches
    }
}