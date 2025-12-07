use crate::service::{Service, ServiceError, IInputService};
use crate::event::KeyCode;
use crate::event_bus::EventBus;
use super::{InputState, KeyboardState, MouseState, Touch};

pub struct InputServiceImpl {
    state: InputState,
    event_bus: Option<EventBus>,
}

impl InputServiceImpl {
    pub fn new() -> Self {
        Self {
            state: InputState::new(),
            event_bus: None,
        }
    }
    
    pub fn set_event_bus(&mut self, event_bus: EventBus) {
        self.event_bus = Some(event_bus);
    }
}

impl Service for InputServiceImpl {
    fn name(&self) -> &str {
        "input"
    }
    
    fn initialize(&mut self) -> Result<(), ServiceError> {
        Ok(())
    }
    
    fn shutdown(&mut self) {
        self.state = InputState::new();
    }
}

impl IInputService for InputServiceImpl {
    fn is_key_down(&self, key: KeyCode) -> bool {
        self.state.is_key_down(key)
    }
    
    fn is_key_pressed(&self, key: KeyCode) -> bool {
        self.state.is_key_pressed(key)
    }
    
    fn get_mouse_position(&self) -> (f32, f32) {
        self.state.get_mouse_position()
    }
}

impl InputServiceImpl {
    pub fn state(&self) -> &InputState {
        &self.state
    }
    
    pub fn state_mut(&mut self) -> &mut InputState {
        &mut self.state
    }
    
    pub fn update(&mut self) {
        self.state.update();
    }
    
    pub fn handle_key_event(&mut self, key: KeyCode, pressed: bool) {
        if pressed {
            self.state.keyboard.key_down(key);
        } else {
            self.state.keyboard.key_up(key);
        }
        
        // 发布事件
        if let Some(event_bus) = &self.event_bus {
            // 这里应该发布KeyEvent
        }
    }
    
    pub fn handle_mouse_move(&mut self, x: f32, y: f32) {
        let old_pos = self.state.mouse.position;
        self.state.mouse.set_position(x, y);
        self.state.mouse.set_delta(x - old_pos.0, y - old_pos.1);
    }
    
    pub fn handle_mouse_button(&mut self, button: usize, pressed: bool) {
        if pressed {
            self.state.mouse.button_down(button);
        } else {
            self.state.mouse.button_up(button);
        }
    }
    
    pub fn handle_touch(&mut self, touch: Touch) {
        // 查找或更新触摸点
        if let Some(existing) = self.state.touches.iter_mut().find(|t| t.id == touch.id) {
            *existing = touch;
        } else {
            self.state.touches.push(touch);
        }
        
        // 移除已结束的触摸点
        self.state.touches.retain(|t| t.phase != super::TouchPhase::Ended && t.phase != super::TouchPhase::Cancelled);
    }
}