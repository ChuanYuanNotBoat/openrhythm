use serde::{Deserialize, Serialize};
use semver::VersionReq;
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModManifest {
    pub metadata: ModMetadata,
    pub dependencies: ModDependencies,
    pub compatibility: ModCompatibility,
    pub entrypoints: ModEntrypoints,
    pub resources: ModResources,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModMetadata {
    pub id: String,
    pub name: String,
    pub version: String,
    pub author: String,
    pub description: Option<String>,
    pub license: Option<String>,
    pub homepage: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModDependencies {
    pub core: VersionReq,
    pub mods: HashMap<String, VersionReq>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModCompatibility {
    #[serde(default = "default_api_version")]
    pub api_version: String,
    pub min_core_version: VersionReq,
    pub platforms: Vec<String>,
}

fn default_api_version() -> String {
    "1.0".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModEntrypoints {
    pub gameplay: Option<String>,
    pub ui: Option<String>,
    pub services: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModResources {
    pub scripts: Vec<PathBuf>,
    pub assets: Vec<PathBuf>,
    pub configs: Vec<PathBuf>,
}

impl Default for ModDependencies {
    fn default() -> Self {
        Self {
            core: VersionReq::parse("^1.0.0").unwrap(),
            mods: HashMap::new(),
        }
    }
}

impl Default for ModCompatibility {
    fn default() -> Self {
        Self {
            api_version: "1.0".to_string(),
            min_core_version: VersionReq::parse("^1.0.0").unwrap(),
            platforms: vec![
                "windows".to_string(),
                "linux".to_string(),
                "macos".to_string(),
                "android".to_string(),
                "ios".to_string(),
            ],
        }
    }
}

impl Default for ModEntrypoints {
    fn default() -> Self {
        Self {
            gameplay: None,
            ui: None,
            services: HashMap::new(),
        }
    }
}

impl Default for ModResources {
    fn default() -> Self {
        Self {
            scripts: Vec::new(),
            assets: Vec::new(),
            configs: Vec::new(),
        }
    }
}