use glam::Vec2;

#[derive(Debug, Clone)]
pub struct Touch {
    pub id: u64,
    pub position: Vec2,
    pub phase: TouchPhase,
    pub pressure: f32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TouchPhase {
    Began,
    Moved,
    Ended,
    Cancelled,
}

impl Touch {
    pub fn new(id: u64, x: f32, y: f32, phase: TouchPhase) -> Self {
        Self {
            id,
            position: Vec2::new(x, y),
            phase,
            pressure: 1.0,
        }
    }
    
    pub fn with_pressure(mut self, pressure: f32) -> Self {
        self.pressure = pressure;
        self
    }
}