fn main() {
    pyo3_build_config::add_extension_module_link_args();
    
    // 添加跨平台编译配置
    if cfg!(target_os = "windows") {
        println!("cargo:rustc-link-arg=/SUBSYSTEM:WINDOWS");
        println!("cargo:rustc-link-arg=/ENTRY:mainCRTStartup");
    }
    
    // 配置PyO3
    println!("cargo:rustc-cfg=Py_3_8");
    println!("cargo:rustc-cfg=Py_LIMITED_API");
}