// Minimal stub for mod system registry to satisfy compilation while
// implementing a lightweight interface used by other modules.

#[derive(Debug, Default)]
pub struct Registry {}

impl Registry {
    pub fn new() -> Self {
        Registry {}
    }
}

pub type RegistryId = String;

// Keep API minimal; expand later when functionality is needed.
