use crate::event::KeyCode;
use std::collections::HashMap;

#[derive(Debug, Clone, Default)]
pub struct KeyboardState {
    keys_down: HashMap<KeyCode, bool>,
    keys_pressed: HashMap<KeyCode, bool>,
    keys_released: HashMap<KeyCode, bool>,
}

impl KeyboardState {
    pub fn new() -> Self {
        Self::default()
    }
    
    pub fn key_down(&mut self, key: KeyCode) {
        if !self.is_key_down(key) {
            self.keys_pressed.insert(key, true);
        }
        self.keys_down.insert(key, true);
    }
    
    pub fn key_up(&mut self, key: KeyCode) {
        self.keys_down.insert(key, false);
        self.keys_released.insert(key, true);
    }
    
    pub fn is_key_down(&self, key: KeyCode) -> bool {
        *self.keys_down.get(&key).unwrap_or(&false)
    }
    
    pub fn is_key_pressed(&self, key: KeyCode) -> bool {
        *self.keys_pressed.get(&key).unwrap_or(&false)
    }
    
    pub fn is_key_released(&self, key: KeyCode) -> bool {
        *self.keys_released.get(&key).unwrap_or(&false)
    }
    
    pub fn update(&mut self) {
        // 清除瞬时状态
        self.keys_pressed.clear();
        self.keys_released.clear();
    }
    
    pub fn reset(&mut self) {
        self.keys_down.clear();
        self.keys_pressed.clear();
        self.keys_released.clear();
    }
    
    pub fn set_key_state(&mut self, key: KeyCode, down: bool) {
        if down {
            self.key_down(key);
        } else {
            self.key_up(key);
        }
    }
}

// 键盘映射
pub struct KeyMapping {
    pub left: Vec<KeyCode>,
    pub right: Vec<KeyCode>,
    pub up: Vec<KeyCode>,
    pub down: Vec<KeyCode>,
    pub confirm: Vec<KeyCode>,
    pub cancel: Vec<KeyCode>,
    pub pause: Vec<KeyCode>,
}

impl Default for KeyMapping {
    fn default() -> Self {
        Self {
            left: vec![KeyCode::Left, KeyCode::A],
            right: vec![KeyCode::Right, KeyCode::D],
            up: vec![KeyCode::Up, KeyCode::W],
            down: vec![KeyCode::Down, KeyCode::S],
            confirm: vec![KeyCode::Enter, KeyCode::Space, KeyCode::Z],
            cancel: vec![KeyCode::Escape, KeyCode::Backspace, KeyCode::X],
            pause: vec![KeyCode::Escape, KeyCode::P],
        }
    }
}

impl KeyMapping {
    pub fn for_4k() -> Self {
        Self {
            left: vec![KeyCode::D, KeyCode::F],
            right: vec![KeyCode::J, KeyCode::K],
            up: vec![KeyCode::Space, KeyCode::W],
            down: vec![KeyCode::S],
            confirm: vec![KeyCode::Enter, KeyCode::Space],
            cancel: vec![KeyCode::Escape, KeyCode::Backspace],
            pause: vec![KeyCode::Escape, KeyCode::P],
        }
    }
    
    pub fn is_left_pressed(&self, keyboard: &KeyboardState) -> bool {
        self.left.iter().any(|&key| keyboard.is_key_pressed(key))
    }
    
    pub fn is_left_down(&self, keyboard: &KeyboardState) -> bool {
        self.left.iter().any(|&key| keyboard.is_key_down(key))
    }
    
    pub fn is_right_pressed(&self, keyboard: &KeyboardState) -> bool {
        self.right.iter().any(|&key| keyboard.is_key_pressed(key))
    }
    
    pub fn is_right_down(&self, keyboard: &KeyboardState) -> bool {
        self.right.iter().any(|&key| keyboard.is_key_down(key))
    }
}