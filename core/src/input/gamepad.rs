#[derive(Debug, Clone, Default)]
pub struct GamepadState {
    pub id: u32,
    pub connected: bool,
    pub axes: [f32; 6], // 左摇杆X,Y，右摇杆X,Y，左扳机，右扳机
    pub buttons: [bool; 16],
    pub buttons_pressed: [bool; 16],
    pub buttons_released: [bool; 16],
}

impl GamepadState {
    pub fn new(id: u32) -> Self {
        Self {
            id,
            connected: true,
            axes: [0.0; 6],
            buttons: [false; 16],
            buttons_pressed: [false; 16],
            buttons_released: [false; 16],
        }
    }
    
    pub fn set_axis(&mut self, axis: usize, value: f32) {
        if axis < 6 {
            self.axes[axis] = value;
        }
    }
    
    pub fn get_axis(&self, axis: usize) -> f32 {
        if axis < 6 { self.axes[axis] } else { 0.0 }
    }
    
    pub fn button_down(&mut self, button: usize) {
        if button < 16 {
            if !self.buttons[button] {
                self.buttons_pressed[button] = true;
            }
            self.buttons[button] = true;
        }
    }
    
    pub fn button_up(&mut self, button: usize) {
        if button < 16 {
            self.buttons[button] = false;
            self.buttons_released[button] = true;
        }
    }
    
    pub fn is_button_down(&self, button: usize) -> bool {
        if button < 16 { self.buttons[button] } else { false }
    }
    
    pub fn is_button_pressed(&self, button: usize) -> bool {
        if button < 16 { self.buttons_pressed[button] } else { false }
    }
    
    pub fn update(&mut self) {
        self.buttons_pressed.fill(false);
        self.buttons_released.fill(false);
    }
    
    pub fn reset(&mut self) {
        self.connected = false;
        self.axes.fill(0.0);
        self.buttons.fill(false);
        self.buttons_pressed.fill(false);
        self.buttons_released.fill(false);
    }
}

#[derive(Debug, Clone, Copy)]
pub enum GamepadButton {
    A = 0,
    B = 1,
    X = 2,
    Y = 3,
    LeftBumper = 4,
    RightBumper = 5,
    Back = 6,
    Start = 7,
    Guide = 8,
    LeftThumb = 9,
    RightThumb = 10,
    DPadUp = 11,
    DPadRight = 12,
    DPadDown = 13,
    DPadLeft = 14,
}

#[derive(Debug, Clone, Copy)]
pub enum GamepadAxis {
    LeftX = 0,
    LeftY = 1,
    RightX = 2,
    RightY = 3,
    LeftTrigger = 4,
    RightTrigger = 5,
}