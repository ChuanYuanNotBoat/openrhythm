use glam::Vec2;

#[derive(Debug, Clone, Default)]
pub struct MouseState {
    pub position: (f32, f32),
    pub delta: (f32, f32),
    pub buttons: [bool; 3], // 左键、右键、中键
    pub buttons_pressed: [bool; 3],
    pub buttons_released: [bool; 3],
    pub scroll_delta: (f32, f32),
}

impl MouseState {
    pub fn new() -> Self {
        Self::default()
    }
    
    pub fn set_position(&mut self, x: f32, y: f32) {
        self.position = (x, y);
    }
    
    pub fn set_delta(&mut self, dx: f32, dy: f32) {
        self.delta = (dx, dy);
    }
    
    pub fn button_down(&mut self, button: usize) {
        if button < 3 {
            if !self.buttons[button] {
                self.buttons_pressed[button] = true;
            }
            self.buttons[button] = true;
        }
    }
    
    pub fn button_up(&mut self, button: usize) {
        if button < 3 {
            self.buttons[button] = false;
            self.buttons_released[button] = true;
        }
    }
    
    pub fn is_button_down(&self, button: usize) -> bool {
        if button < 3 { self.buttons[button] } else { false }
    }
    
    pub fn is_button_pressed(&self, button: usize) -> bool {
        if button < 3 { self.buttons_pressed[button] } else { false }
    }
    
    pub fn is_button_released(&self, button: usize) -> bool {
        if button < 3 { self.buttons_released[button] } else { false }
    }
    
    pub fn set_scroll_delta(&mut self, x: f32, y: f32) {
        self.scroll_delta = (x, y);
    }
    
    pub fn update(&mut self) {
        // 重置瞬时状态
        self.delta = (0.0, 0.0);
        self.buttons_pressed.fill(false);
        self.buttons_released.fill(false);
        self.scroll_delta = (0.0, 0.0);
    }
    
    pub fn reset(&mut self) {
        self.position = (0.0, 0.0);
        self.delta = (0.0, 0.0);
        self.buttons.fill(false);
        self.buttons_pressed.fill(false);
        self.buttons_released.fill(false);
        self.scroll_delta = (0.0, 0.0);
    }
}

#[derive(Debug, Clone, Copy)]
pub enum MouseButton {
    Left = 0,
    Right = 1,
    Middle = 2,
}