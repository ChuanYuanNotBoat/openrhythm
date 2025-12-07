use std::collections::HashMap;
use crate::error::Result;

#[derive(Clone)]
pub struct EventId {
    pub id: String,
}

impl EventId {
    pub fn new(id: &str) -> Self { Self { id: id.to_string() } }
}

pub struct EventBus {
    // minimal placeholder
    handlers: HashMap<String, Vec<Box<dyn Fn(&serde_json::Value) + Send + Sync>>>,
}

impl EventBus {
    pub fn new() -> Self {
        Self { handlers: HashMap::new() }
    }

    pub fn publish(&self, _event_type: &str, _data: &serde_json::Value) {
        // no-op placeholder
    }
}
