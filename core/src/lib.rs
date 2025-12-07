pub mod error;
pub mod config;
pub mod event;
pub mod event_bus;
pub mod service;
pub mod mod_system;
pub mod audio;
pub mod chart;
pub mod input;
pub mod rendering;
pub mod resource;
mod bindings;

use pyo3::prelude::*;
use pyo3::types::PyModule;
pub use error::*;
pub use config::*;
pub use event::*;
pub use service::*;
pub use mod_system::*;
pub use audio::*;
pub use chart::*;
pub use input::*;
pub use rendering::*;
pub use resource::*;

#[pymodule]
fn openrhythm_core(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    // 修正 pyo3 0.20 的 API 签名
    // 先注册一些基础类型
    
    // 注册错误类型
    m.add_class::<PyCoreError>()?;
    
    // 注册配置类型
    m.add_class::<PyCoreConfig>()?;
    
    // 注册事件总线
    m.add_class::<PyEventBus>()?;
    
    // 注册事件ID
    m.add_class::<PyEventId>()?;
    
    // 注册服务容器
    m.add_class::<PyServiceContainer>()?;
    
    // 注册模块加载器
    m.add_class::<PyModLoader>()?;
    
    // 注册模块清单
    m.add_class::<PyModManifest>()?;
    
    // 注册颜色类型
    m.add_class::<PyColor>()?;
    
    // 注册向量类型
    m.add_class::<PyVector2>()?;
    m.add_class::<PyVector3>()?;
    
    // 注册输入状态
    m.add_class::<PyInputState>()?;
    
    // 注册键码枚举
    m.add_class::<PyKeyCode>()?;
    
    // 注册资源管理器
    m.add_class::<PyResourceManager>()?;
    
    Ok(())
}

// 修复 PyCoreError 实现 Send + Sync
#[pyclass]
#[derive(Clone)]
struct PyCoreError {
    inner: error::CoreError,
}

#[pymethods]
impl PyCoreError {
    #[new]
    fn new(message: String) -> Self {
        Self {
            inner: error::CoreError::Generic(message),
        }
    }
    
    fn __str__(&self) -> String {
        format!("{}", self.inner)
    }
}

#[pyclass]
#[derive(Clone)]
struct PyCoreConfig {
    inner: config::CoreConfig,
}

#[pymethods]
impl PyCoreConfig {
    #[new]
    fn new() -> Self {
        Self {
            inner: config::CoreConfig::default(),
        }
    }
    
    #[getter]
    fn window_width(&self) -> u32 {
        self.inner.window.width
    }
    
    #[setter]
    fn set_window_width(&mut self, width: u32) {
        self.inner.window.width = width;
    }
}

#[pyclass]
struct PyEventBus {
    inner: event::EventBus,
}

#[pymethods]
impl PyEventBus {
    #[new]
    fn new() -> Self {
        Self {
            inner: event::EventBus::new(),
        }
    }
    
    fn publish(&self, _py: Python, _event_type: &str, _event_data: Py<PyAny>) -> PyResult<()> {
        // Compatibility stub: accept Python data but do not process it yet.
        Ok(())
    }
}

#[pyclass]
struct PyEventId {
    inner: event::EventId,
}

#[pyclass]
struct PyServiceContainer {
    inner: service::ServiceContainer,
}

#[pymethods]
impl PyServiceContainer {
    #[new]
    fn new() -> Self {
        Self {
            inner: service::ServiceContainer::new(),
        }
    }
}

#[pyclass]
struct PyModLoader {
    inner: mod_system::ModLoader,
}

#[pymethods]
impl PyModLoader {
    #[new]
    fn new(mods_dir: String) -> Self {
        Self {
            inner: mod_system::ModLoader::new(std::path::PathBuf::from(mods_dir)),
        }
    }
    
    fn scan_mods(&mut self) -> PyResult<Vec<String>> {
        self.inner.scan_mods()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("{}", e)))
    }
}

#[pyclass]
struct PyModManifest {
    inner: mod_system::ModManifest,
}

#[pyclass]
#[derive(Clone)]
struct PyColor {
    inner: rendering::Color,
}

#[pymethods]
impl PyColor {
    #[new]
    fn new(r: f32, g: f32, b: f32, a: f32) -> Self {
        Self {
            inner: rendering::Color::rgba(r, g, b, a),
        }
    }
    
    #[staticmethod]
    fn white() -> Self {
        Self { inner: rendering::Color::WHITE }
    }
    
    #[staticmethod]
    fn black() -> Self {
        Self { inner: rendering::Color::BLACK }
    }
    
    #[staticmethod]
    fn red() -> Self {
        Self { inner: rendering::Color::RED }
    }
    
    #[staticmethod]
    fn green() -> Self {
        Self { inner: rendering::Color::GREEN }
    }
    
    #[staticmethod]
    fn blue() -> Self {
        Self { inner: rendering::Color::BLUE }
    }
    
    #[getter]
    fn r(&self) -> f32 {
        self.inner.r
    }
    
    #[getter]
    fn g(&self) -> f32 {
        self.inner.g
    }
    
    #[getter]
    fn b(&self) -> f32 {
        self.inner.b
    }
    
    #[getter]
    fn a(&self) -> f32 {
        self.inner.a
    }
}

#[pyclass]
#[derive(Clone)]
struct PyVector2 {
    inner: glam::Vec2,
}

#[pymethods]
impl PyVector2 {
    #[new]
    fn new(x: f32, y: f32) -> Self {
        Self {
            inner: glam::Vec2::new(x, y),
        }
    }
    
    #[getter]
    fn x(&self) -> f32 {
        self.inner.x
    }
    
    #[getter]
    fn y(&self) -> f32 {
        self.inner.y
    }
    
    fn __add__(&self, other: &PyVector2) -> PyVector2 {
        PyVector2 {
            inner: self.inner + other.inner,
        }
    }
    
    fn __sub__(&self, other: &PyVector2) -> PyVector2 {
        PyVector2 {
            inner: self.inner - other.inner,
        }
    }
    
    fn __mul__(&self, scalar: f32) -> PyVector2 {
        PyVector2 {
            inner: self.inner * scalar,
        }
    }
    
    fn __str__(&self) -> String {
        format!("Vector2({}, {})", self.inner.x, self.inner.y)
    }
}

#[pyclass]
#[derive(Clone)]
struct PyVector3 {
    inner: glam::Vec3,
}

#[pymethods]
impl PyVector3 {
    #[new]
    fn new(x: f32, y: f32, z: f32) -> Self {
        Self {
            inner: glam::Vec3::new(x, y, z),
        }
    }
    
    #[getter]
    fn x(&self) -> f32 {
        self.inner.x
    }
    
    #[getter]
    fn y(&self) -> f32 {
        self.inner.y
    }
    
    #[getter]
    fn z(&self) -> f32 {
        self.inner.z
    }
}

#[pyclass]
struct PyInputState {
    inner: input::InputState,
}

#[pymethods]
impl PyInputState {
    #[new]
    fn new() -> Self {
        Self {
            inner: input::InputState::new(),
        }
    }
    
    fn is_key_down(&self, key: PyKeyCode) -> bool {
        self.inner.is_key_down(key.into())
    }
    
    fn is_key_pressed(&self, key: PyKeyCode) -> bool {
        self.inner.is_key_pressed(key.into())
    }
    
    fn get_mouse_position(&self) -> (f32, f32) {
        self.inner.get_mouse_position()
    }
}

#[pyclass]
#[derive(Clone, Copy)]
enum PyKeyCode {
    A, B, C, D, E, F, G, H, I, J, K, L, M,
    N, O, P, Q, R, S, T, U, V, W, X, Y, Z,
    Key0, Key1, Key2, Key3, Key4,
    Key5, Key6, Key7, Key8, Key9,
    F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12,
    Space, Enter, Escape, Tab, Backspace,
    Left, Right, Up, Down,
    DF, JK, AS, KL,
}

impl From<PyKeyCode> for event::KeyCode {
    fn from(py_key: PyKeyCode) -> Self {
        match py_key {
            PyKeyCode::A => event::KeyCode::A,
            PyKeyCode::B => event::KeyCode::B,
            PyKeyCode::C => event::KeyCode::C,
            PyKeyCode::D => event::KeyCode::D,
            PyKeyCode::E => event::KeyCode::E,
            PyKeyCode::F => event::KeyCode::F,
            PyKeyCode::G => event::KeyCode::G,
            PyKeyCode::H => event::KeyCode::H,
            PyKeyCode::I => event::KeyCode::I,
            PyKeyCode::J => event::KeyCode::J,
            PyKeyCode::K => event::KeyCode::K,
            PyKeyCode::L => event::KeyCode::L,
            PyKeyCode::M => event::KeyCode::M,
            PyKeyCode::N => event::KeyCode::N,
            PyKeyCode::O => event::KeyCode::O,
            PyKeyCode::P => event::KeyCode::P,
            PyKeyCode::Q => event::KeyCode::Q,
            PyKeyCode::R => event::KeyCode::R,
            PyKeyCode::S => event::KeyCode::S,
            PyKeyCode::T => event::KeyCode::T,
            PyKeyCode::U => event::KeyCode::U,
            PyKeyCode::V => event::KeyCode::V,
            PyKeyCode::W => event::KeyCode::W,
            PyKeyCode::X => event::KeyCode::X,
            PyKeyCode::Y => event::KeyCode::Y,
            PyKeyCode::Z => event::KeyCode::Z,
            PyKeyCode::Key0 => event::KeyCode::Key0,
            PyKeyCode::Key1 => event::KeyCode::Key1,
            PyKeyCode::Key2 => event::KeyCode::Key2,
            PyKeyCode::Key3 => event::KeyCode::Key3,
            PyKeyCode::Key4 => event::KeyCode::Key4,
            PyKeyCode::Key5 => event::KeyCode::Key5,
            PyKeyCode::Key6 => event::KeyCode::Key6,
            PyKeyCode::Key7 => event::KeyCode::Key7,
            PyKeyCode::Key8 => event::KeyCode::Key8,
            PyKeyCode::Key9 => event::KeyCode::Key9,
            PyKeyCode::F1 => event::KeyCode::F1,
            PyKeyCode::F2 => event::KeyCode::F2,
            PyKeyCode::F3 => event::KeyCode::F3,
            PyKeyCode::F4 => event::KeyCode::F4,
            PyKeyCode::F5 => event::KeyCode::F5,
            PyKeyCode::F6 => event::KeyCode::F6,
            PyKeyCode::F7 => event::KeyCode::F7,
            PyKeyCode::F8 => event::KeyCode::F8,
            PyKeyCode::F9 => event::KeyCode::F9,
            PyKeyCode::F10 => event::KeyCode::F10,
            PyKeyCode::F11 => event::KeyCode::F11,
            PyKeyCode::F12 => event::KeyCode::F12,
            PyKeyCode::Space => event::KeyCode::Space,
            PyKeyCode::Enter => event::KeyCode::Enter,
            PyKeyCode::Escape => event::KeyCode::Escape,
            PyKeyCode::Tab => event::KeyCode::Tab,
            PyKeyCode::Backspace => event::KeyCode::Backspace,
            PyKeyCode::Left => event::KeyCode::Left,
            PyKeyCode::Right => event::KeyCode::Right,
            PyKeyCode::Up => event::KeyCode::Up,
            PyKeyCode::Down => event::KeyCode::Down,
            PyKeyCode::DF => event::KeyCode::DF,
            PyKeyCode::JK => event::KeyCode::JK,
            PyKeyCode::AS => event::KeyCode::AS,
            PyKeyCode::KL => event::KeyCode::KL,
        }
    }
}

#[pyclass]
struct PyResourceManager {
    inner: resource::ResourceManager,
}

#[pymethods]
impl PyResourceManager {
    #[new]
    fn new(max_cache_size: usize) -> Self {
        Self {
            inner: resource::ResourceManager::new(max_cache_size),
        }
    }
    
    fn add_search_path(&mut self, path: String) {
        self.inner.add_search_path(std::path::PathBuf::from(path));
    }
    
    fn load_text(&self, path: String) -> PyResult<String> {
        // 注意：这里简化了，实际应该返回Arc<String>，把这个补充
        Ok("Not implemented".to_string())
    }
}