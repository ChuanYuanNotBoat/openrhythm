use serde::{Deserialize, Serialize};
use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use uuid::Uuid;

// 事件标识符
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EventId(Uuid);

impl EventId {
    pub fn new() -> Self {
        Self(Uuid::new_v4())
    }
}

impl Default for EventId {
    fn default() -> Self {
        Self::new()
    }
}

// 事件特征
pub trait Event: Any + Send + Sync {
    fn type_id(&self) -> TypeId {
        TypeId::of::<Self>()
    }
    
    fn as_any(&self) -> &dyn Any;
    
    fn as_any_mut(&mut self) -> &mut dyn Any;
}

// 事件包装器
pub struct EventBox(Box<dyn Event>);

impl EventBox {
    pub fn new<T: Event>(event: T) -> Self {
        Self(Box::new(event))
    }

    // 返回对内部事件的引用（如果类型匹配）
    pub fn downcast_ref<T: Event>(&self) -> Option<&T> {
        self.0.as_any().downcast_ref::<T>()
    }

    pub fn is<T: Event>(&self) -> bool {
        self.0.as_any().is::<T>()
    }
}

impl std::fmt::Debug for EventBox {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EventBox").finish()
    }
}

// 事件监听器
pub type EventCallback = Box<dyn Fn(&dyn Event) + Send + Sync>;

// 事件总线
#[derive(Clone)]
pub struct EventBus {
    listeners: Arc<RwLock<HashMap<TypeId, Vec<(EventId, EventCallback)>>>>,
}

impl EventBus {
    pub fn new() -> Self {
        Self {
            listeners: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    pub fn subscribe<T: Event + 'static>(&self, callback: EventCallback) -> EventId {
        let type_id = TypeId::of::<T>();
        let id = EventId::new();
        
        let mut listeners = self.listeners.write().unwrap();
        listeners.entry(type_id).or_insert_with(Vec::new).push((id, callback));
        
        id
    }
    
    pub fn unsubscribe(&self, id: EventId) {
        let mut listeners = self.listeners.write().unwrap();
        
        for callbacks in listeners.values_mut() {
            callbacks.retain(|(callback_id, _)| *callback_id != id);
        }
    }
    
    pub fn publish<T: Event + 'static>(&self, event: T) {
        let type_id = TypeId::of::<T>();
        
        if let Ok(listeners) = self.listeners.read() {
            if let Some(callbacks) = listeners.get(&type_id) {
                for (_, callback) in callbacks {
                    callback(&event);
                }
            }
        }
    }
    
    pub fn publish_async<T: Event + 'static + Clone>(&self, event: T) -> tokio::task::JoinHandle<()> {
        let event_bus = self.clone();
        tokio::task::spawn(async move {
            event_bus.publish(event);
        })
    }
}

// 预定义事件类型
#[derive(Debug, Clone)]
pub struct SystemStartEvent {
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl Event for SystemStartEvent {
    fn as_any(&self) -> &dyn Any { self }
    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

#[derive(Debug, Clone)]
pub struct SystemExitEvent {
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl Event for SystemExitEvent {
    fn as_any(&self) -> &dyn Any { self }
    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

// 输入事件
#[derive(Debug, Clone)]
pub struct KeyEvent {
    pub key: KeyCode,
    pub state: KeyState,
    pub timestamp: f64,
}

impl Event for KeyEvent {
    fn as_any(&self) -> &dyn Any { self }
    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyState {
    Pressed,
    Released,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum KeyCode {
    // 字母键
    A, B, C, D, E, F, G, H, I, J, K, L, M,
    N, O, P, Q, R, S, T, U, V, W, X, Y, Z,
    
    // 数字键
    Key0, Key1, Key2, Key3, Key4,
    Key5, Key6, Key7, Key8, Key9,
    
    // 功能键
    F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12,
    
    // 其他键
    Space, Enter, Escape, Tab, Backspace,
    Left, Right, Up, Down,
    
    // 4K音游常用键
    DF, JK, AS, KL,  // 常用配置
}

// 音频事件
#[derive(Debug, Clone)]
pub struct AudioPlayEvent {
    pub sound_id: String,
    pub volume: f32,
    pub looped: bool,
}

impl Event for AudioPlayEvent {
    fn as_any(&self) -> &dyn Any { self }
    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

// 渲染事件
#[derive(Debug, Clone)]
pub struct FrameBeginEvent {
    pub frame_number: u64,
    pub delta_time: f32,
}

impl Event for FrameBeginEvent {
    fn as_any(&self) -> &dyn Any { self }
    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}