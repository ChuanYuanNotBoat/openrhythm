use super::manifest::ModManifest;
use crate::error::{CoreError, Result};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use semver::VersionReq;

pub struct ModLoader {
    mods_dir: PathBuf,
    loaded_mods: HashMap<String, ModInfo>,
}

pub struct ModInfo {
    pub manifest: ModManifest,
    pub path: PathBuf,
    pub dependencies: Vec<String>,
    pub state: ModState,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ModState {
    Unloaded,
    Loaded,
    Active,
    Error(String),
}

impl ModLoader {
    pub fn new(mods_dir: PathBuf) -> Self {
        Self {
            mods_dir,
            loaded_mods: HashMap::new(),
        }
    }
    
    pub fn scan_mods(&mut self) -> Result<Vec<String>> {
        let mut mod_ids = Vec::new();
        
        for entry in fs::read_dir(&self.mods_dir)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                if let Some(mod_id) = self.load_mod_manifest(&path)? {
                    mod_ids.push(mod_id);
                }
            }
        }
        
        Ok(mod_ids)
    }
    
    fn load_mod_manifest(&mut self, mod_path: &Path) -> Result<Option<String>> {
        let manifest_path = mod_path.join("mod.toml");
        
        if !manifest_path.exists() {
            return Ok(None);
        }
        
        let manifest_content = fs::read_to_string(&manifest_path)?;
        let manifest: ModManifest = toml::from_str(&manifest_content)
            .map_err(|e| CoreError::ModLoading(format!("Failed to parse manifest: {}", e)))?;
        
        let mod_id = manifest.metadata.id.clone();
        
        self.loaded_mods.insert(mod_id.clone(), ModInfo {
            manifest,
            path: mod_path.to_path_buf(),
            dependencies: Vec::new(),
            state: ModState::Unloaded,
        });
        
        Ok(Some(mod_id))
    }
    
    pub fn resolve_dependencies(&mut self) -> Result<Vec<String>> {
        let mut resolved = Vec::new();
        let mut visited = HashSet::new();
        let mut temp_visited = HashSet::new();
        
        for mod_id in self.loaded_mods.keys().cloned().collect::<Vec<_>>() {
            if !visited.contains(&mod_id) {
                self.visit_dependencies(
                    &mod_id, 
                    &mut visited, 
                    &mut temp_visited, 
                    &mut resolved
                )?;
            }
        }
        
        Ok(resolved)
    }
    
    fn visit_dependencies(
        &mut self,
        mod_id: &str,
        visited: &mut HashSet<String>,
        temp_visited: &mut HashSet<String>,
        resolved: &mut Vec<String>,
    ) -> Result<()> {
        if temp_visited.contains(mod_id) {
            return Err(CoreError::ModLoading(
                format!("Circular dependency detected involving mod: {}", mod_id)
            ));
        }
        
        if visited.contains(mod_id) {
            return Ok(());
        }
        
        temp_visited.insert(mod_id.to_string());
        
        let mod_info = self.loaded_mods.get_mut(mod_id)
            .ok_or_else(|| CoreError::ModLoading(format!("Mod not found: {}", mod_id)))?;
        
        // 收集依赖
        let mut deps = Vec::new();
        for (dep_id, _) in &mod_info.manifest.dependencies.mods {
            deps.push(dep_id.clone());
        }
        
        mod_info.dependencies = deps.clone();
        
        // 递归处理依赖
        for dep_id in deps {
            self.visit_dependencies(&dep_id, visited, temp_visited, resolved)?;
        }
        
        temp_visited.remove(mod_id);
        visited.insert(mod_id.to_string());
        resolved.push(mod_id.to_string());
        
        Ok(())
    }
    
    pub fn get_mod_info(&self, mod_id: &str) -> Option<&ModInfo> {
        self.loaded_mods.get(mod_id)
    }
    
    pub fn get_active_mods(&self) -> Vec<&ModInfo> {
        self.loaded_mods.values()
            .filter(|info| info.state == ModState::Active)
            .collect()
    }
}