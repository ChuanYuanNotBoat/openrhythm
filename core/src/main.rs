use openrhythm_core::{
    config::CoreConfig,
    event::{EventBus, SystemStartEvent},
    service::ServiceContainer,
    mod_system::ModLoader,
    audio::AudioServiceImpl,
    input::InputServiceImpl,
    rendering::Renderer,
    resource::ResourceManager,
    error::Result,
};
use winit::{
    event::{Event, WindowEvent, ElementState, KeyEvent as WinitKeyEvent},
    event_loop::{ControlFlow, EventLoop},
    window::WindowBuilder,
    keyboard::KeyCode as WinitKeyCode,
};
use chrono::Utc;
use std::path::PathBuf;
use std::sync::Arc;

// 引入 chart_manager
use crate::chart_manager::{ChartManager, ChartImportedEvent};

struct Application {
    config: CoreConfig,
    event_bus: EventBus,
    service_container: ServiceContainer,
    mod_loader: ModLoader,
    renderer: Option<Renderer>,
    resource_manager: ResourceManager,
    chart_manager: Option<ChartManager>,
    running: bool,
    window: Option<Arc<winit::window::Window>>,
}

impl Application {
    pub async fn new() -> Result<Self> {
        let config = CoreConfig::default();
        
        let event_bus = EventBus::new();
        let service_container = ServiceContainer::new();
        
        // 创建Mod加载器
        let mod_loader = ModLoader::new(config.paths.mods_dir.clone());
        
        // 创建资源管理器
        let resource_manager = ResourceManager::new(1024 * 1024 * 100); // 100MB缓存
        
        // 创建谱面管理器
        let chart_manager = match ChartManager::new() {
            Ok(manager) => Some(manager),
            Err(e) => {
                log::warn!("Failed to create chart manager: {}", e);
                None
            }
        };
        
        Ok(Self {
            config,
            event_bus,
            service_container,
            mod_loader,
            renderer: None,
            resource_manager,
            chart_manager,
            running: false,
            window: None,
        })
    }
    
    pub async fn initialize(&mut self) -> Result<()> {
        log::info!("Initializing OpenRhythm...");
        
        // 创建窗口
        let event_loop = EventLoop::new()?;
        let window = Arc::new(WindowBuilder::new()
            .with_title("OpenRhythm")
            .with_inner_size(winit::dpi::LogicalSize::new(
                self.config.window.width as f64,
                self.config.window.height as f64,
            ))
            .build(&event_loop)?);
        
        self.window = Some(window.clone());
        
        // 初始化渲染器
        let renderer = Renderer::new(window.clone()).await?;
        self.renderer = Some(renderer);
        
        // 初始化服务
        self.initialize_services()?;
        
        // 初始化资源管理器
        self.initialize_resource_manager()?;
        
        // 扫描和加载Mod
        self.scan_and_load_mods()?;
        
        // 初始化谱面管理器
        if let Some(manager) = &self.chart_manager {
            let charts = manager.get_all_charts();
            log::info!("Found {} charts in library", charts.len());
        }
        
        // 发布系统启动事件
        self.event_bus.publish(SystemStartEvent {
            timestamp: Utc::now(),
        });
        
        self.running = true;
        
        log::info!("OpenRhythm initialized successfully");
        
        // 运行主循环
        self.run(event_loop).await?;
        
        Ok(())
    }
    
    fn initialize_services(&mut self) -> Result<()> {
        // 注册音频服务
        let audio_service = AudioServiceImpl::new(self.config.audio.latency_target_ms);
        self.service_container.register(audio_service)?;
        
        // 注册输入服务
        let mut input_service = InputServiceImpl::new();
        input_service.set_event_bus(self.event_bus.clone());
        self.service_container.register(input_service)?;
        
        // 初始化所有服务
        self.service_container.initialize_all()?;
        
        Ok(())
    }
    
    fn initialize_resource_manager(&mut self) -> Result<()> {
        // 添加搜索路径
        self.resource_manager.add_search_path(self.config.paths.assets_dir.clone());
        self.resource_manager.add_search_path(self.config.paths.mods_dir.clone());
        
        // 注册加载器
        if let Some(renderer) = &self.renderer {
            let device = renderer.device();
            let queue = renderer.queue();
            
            let texture_loader = super::resource::loader::TextureLoader::new(device, queue);
            self.resource_manager.register_loader(texture_loader);
        }
        
        let audio_loader = super::resource::loader::AudioLoader;
        self.resource_manager.register_loader(audio_loader);
        
        let text_loader = super::resource::loader::TextLoader;
        self.resource_manager.register_loader(text_loader);
        
        Ok(())
    }
    
    fn scan_and_load_mods(&mut self) -> Result<()> {
        log::info!("Scanning for mods...");
        
        let mod_ids = self.mod_loader.scan_mods()?;
        log::info!("Found {} mods: {:?}", mod_ids.len(), mod_ids);
        
        // 解析依赖关系
        let load_order = self.mod_loader.resolve_dependencies()?;
        log::info!("Mod load order: {:?}", load_order);
        
        Ok(())
    }
    
    async fn run(&mut self, event_loop: EventLoop<()>) -> Result<()> {
        let window = self.window.as_ref().unwrap().clone();
        
        event_loop.run(move |event, elwt| {
            elwt.set_control_flow(ControlFlow::Poll);
            
            match event {
                Event::WindowEvent { event, window_id } if window_id == window.id() => {
                    match event {
                        WindowEvent::CloseRequested => {
                            elwt.exit();
                        }
                        WindowEvent::Resized(size) => {
                            if let Some(renderer) = &mut self.renderer {
                                renderer.resize(size);
                            }
                        }
                        WindowEvent::KeyboardInput { event, .. } => {
                            self.handle_keyboard_input(event);
                        }
                        WindowEvent::CursorMoved { position, .. } => {
                            self.handle_mouse_move(position.x, position.y);
                        }
                        WindowEvent::MouseInput { state, button, .. } => {
                            self.handle_mouse_button(button, state);
                        }
                        WindowEvent::DroppedFile(path) => {
                            // 异步处理拖放文件
                            elwt.set_control_flow(ControlFlow::Wait);
                            
                            // 在实际应用中，这里可能需要使用异步任务
                            // 为了简化，我们直接调用异步函数并等待
                            futures::executor::block_on(async {
                                self.handle_dropped_file(path).await;
                            });
                            
                            elwt.set_control_flow(ControlFlow::Poll);
                        }
                        _ => (),
                    }
                }
                Event::AboutToWait => {
                    // 更新输入状态
                    if let Some(input_service) = self.service_container.get::<InputServiceImpl>() {
                        input_service.update();
                    }
                    
                    // 渲染帧
                    if let Some(renderer) = &mut self.renderer {
                        self.render_frame(renderer);
                    }
                    
                    window.request_redraw();
                }
                Event::RedrawRequested(window_id) if window_id == window.id() => {
                    // 处理重绘
                }
                _ => (),
            }
        })?;
        
        Ok(())
    }
    
    fn handle_keyboard_input(&mut self, event: WinitKeyEvent) {
        if let (Some(physical_key), state) = (event.physical_key, event.state) {
            if let Some(key_code) = self.map_winit_key(physical_key) {
                let pressed = match state {
                    ElementState::Pressed => true,
                    ElementState::Released => false,
                };
                
                if let Some(input_service) = self.service_container.get_mut::<InputServiceImpl>() {
                    input_service.handle_key_event(key_code, pressed);
                }
            }
        }
    }
    
    fn handle_mouse_move(&mut self, x: f64, y: f64) {
        if let Some(input_service) = self.service_container.get_mut::<InputServiceImpl>() {
            input_service.handle_mouse_move(x as f32, y as f32);
        }
    }
    
    fn handle_mouse_button(&mut self, button: winit::event::MouseButton, state: ElementState) {
        let button_index = match button {
            winit::event::MouseButton::Left => 0,
            winit::event::MouseButton::Right => 1,
            winit::event::MouseButton::Middle => 2,
            _ => return,
        };
        
        let pressed = match state {
            ElementState::Pressed => true,
            ElementState::Released => false,
        };
        
        if let Some(input_service) = self.service_container.get_mut::<InputServiceImpl>() {
            input_service.handle_mouse_button(button_index, pressed);
        }
    }
    
    async fn handle_dropped_file(&mut self, path: PathBuf) {
        if let Some(manager) = &self.chart_manager {
            match path.extension().and_then(|s| s.to_str()) {
                Some("mcz") | Some("mc") | Some("json") => {
                    log::info!("Importing chart file: {:?}", path);
                    
                    if path.extension().and_then(|s| s.to_str()) == Some("mcz") {
                        match manager.import_mcz_file(&path) {
                            Ok(charts) => {
                                log::info!("Imported {} charts from {:?}", charts.len(), path);
                                // 发布事件通知UI更新
                                self.event_bus.publish(ChartImportedEvent {
                                    charts: charts.clone(),
                                    source_file: path.to_string_lossy().to_string(),
                                });
                            }
                            Err(e) => {
                                log::error!("Failed to import chart: {}", e);
                            }
                        }
                    } else {
                        // 处理单个谱面文件
                        match self.import_single_chart(&path) {
                            Ok(chart_info) => {
                                log::info!("Imported chart: {}", chart_info.title);
                            }
                            Err(e) => {
                                log::error!("Failed to import chart: {}", e);
                            }
                        }
                    }
                }
                _ => {
                    log::warn!("Unsupported file type: {:?}", path);
                }
            }
        } else {
            log::warn!("Chart manager not available, cannot import file: {:?}", path);
        }
    }
    
    fn import_single_chart(&mut self, path: &PathBuf) -> Result<crate::chart::ChartInfo> {
        // 简化实现 - 实际中需要根据文件类型解析谱面
        // 这里假设有一个函数可以从JSON文件中加载谱面信息
        let content = std::fs::read_to_string(path)?;
        let chart_info: crate::chart::ChartInfo = serde_json::from_str(&content)
            .map_err(|e| crate::error::CoreError::ParseError(format!("Failed to parse chart JSON: {}", e)))?;
        
        Ok(chart_info)
    }
    
    fn render_frame(&mut self, renderer: &mut Renderer) {
        // 开始帧
        let frame = match renderer.begin_frame() {
            Ok(frame) => frame,
            Err(e) => {
                log::error!("Failed to begin frame: {}", e);
                return;
            }
        };
        
        let view = frame.texture.create_view(&wgpu::TextureViewDescriptor::default());
        
        // 创建命令编码器
        let mut encoder = renderer.device().create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("Render Encoder"),
        });
        
        // 开始渲染通道
        {
            let mut render_pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("Render Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color {
                            r: 0.1,
                            g: 0.2,
                            b: 0.3,
                            a: 1.0,
                        }),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                occlusion_query_set: None,
                timestamp_writes: None,
            });
            
            // 这里添加实际的渲染命令
            // 例如：渲染UI、游戏对象等
            
            // 结束渲染通道（作用域结束）
        }
        
        // 提交命令缓冲区
        renderer.queue().submit(std::iter::once(encoder.finish()));
        
        // 结束帧
        renderer.present_frame(frame);
        
        // 更新统计信息
        // 注意：实际帧时间应该通过时间测量获得
        renderer.update_stats(1.0 / 60.0); // 假设60FPS
    }
    
    fn map_winit_key(&self, key: WinitKeyCode) -> Option<crate::event::KeyCode> {
        match key {
            WinitKeyCode::KeyA => Some(crate::event::KeyCode::A),
            WinitKeyCode::KeyB => Some(crate::event::KeyCode::B),
            WinitKeyCode::KeyC => Some(crate::event::KeyCode::C),
            WinitKeyCode::KeyD => Some(crate::event::KeyCode::D),
            WinitKeyCode::KeyE => Some(crate::event::KeyCode::E),
            WinitKeyCode::KeyF => Some(crate::event::KeyCode::F),
            WinitKeyCode::KeyG => Some(crate::event::KeyCode::G),
            WinitKeyCode::KeyH => Some(crate::event::KeyCode::H),
            WinitKeyCode::KeyI => Some(crate::event::KeyCode::I),
            WinitKeyCode::KeyJ => Some(crate::event::KeyCode::J),
            WinitKeyCode::KeyK => Some(crate::event::KeyCode::K),
            WinitKeyCode::KeyL => Some(crate::event::KeyCode::L),
            WinitKeyCode::KeyM => Some(crate::event::KeyCode::M),
            WinitKeyCode::KeyN => Some(crate::event::KeyCode::N),
            WinitKeyCode::KeyO => Some(crate::event::KeyCode::O),
            WinitKeyCode::KeyP => Some(crate::event::KeyCode::P),
            WinitKeyCode::KeyQ => Some(crate::event::KeyCode::Q),
            WinitKeyCode::KeyR => Some(crate::event::KeyCode::R),
            WinitKeyCode::KeyS => Some(crate::event::KeyCode::S),
            WinitKeyCode::KeyT => Some(crate::event::KeyCode::T),
            WinitKeyCode::KeyU => Some(crate::event::KeyCode::U),
            WinitKeyCode::KeyV => Some(crate::event::KeyCode::V),
            WinitKeyCode::KeyW => Some(crate::event::KeyCode::W),
            WinitKeyCode::KeyX => Some(crate::event::KeyCode::X),
            WinitKeyCode::KeyY => Some(crate::event::KeyCode::Y),
            WinitKeyCode::KeyZ => Some(crate::event::KeyCode::Z),
            WinitKeyCode::Digit0 => Some(crate::event::KeyCode::Key0),
            WinitKeyCode::Digit1 => Some(crate::event::KeyCode::Key1),
            WinitKeyCode::Digit2 => Some(crate::event::KeyCode::Key2),
            WinitKeyCode::Digit3 => Some(crate::event::KeyCode::Key3),
            WinitKeyCode::Digit4 => Some(crate::event::KeyCode::Key4),
            WinitKeyCode::Digit5 => Some(crate::event::KeyCode::Key5),
            WinitKeyCode::Digit6 => Some(crate::event::KeyCode::Key6),
            WinitKeyCode::Digit7 => Some(crate::event::KeyCode::Key7),
            WinitKeyCode::Digit8 => Some(crate::event::KeyCode::Key8),
            WinitKeyCode::Digit9 => Some(crate::event::KeyCode::Key9),
            WinitKeyCode::Space => Some(crate::event::KeyCode::Space),
            WinitKeyCode::Enter => Some(crate::event::KeyCode::Enter),
            WinitKeyCode::Escape => Some(crate::event::KeyCode::Escape),
            WinitKeyCode::Tab => Some(crate::event::KeyCode::Tab),
            WinitKeyCode::Backspace => Some(crate::event::KeyCode::Backspace),
            WinitKeyCode::ArrowLeft => Some(crate::event::KeyCode::Left),
            WinitKeyCode::ArrowRight => Some(crate::event::KeyCode::Right),
            WinitKeyCode::ArrowUp => Some(crate::event::KeyCode::Up),
            WinitKeyCode::ArrowDown => Some(crate::event::KeyCode::Down),
            WinitKeyCode::F1 => Some(crate::event::KeyCode::F1),
            WinitKeyCode::F2 => Some(crate::event::KeyCode::F2),
            WinitKeyCode::F3 => Some(crate::event::KeyCode::F3),
            WinitKeyCode::F4 => Some(crate::event::KeyCode::F4),
            WinitKeyCode::F5 => Some(crate::event::KeyCode::F5),
            WinitKeyCode::F6 => Some(crate::event::KeyCode::F6),
            WinitKeyCode::F7 => Some(crate::event::KeyCode::F7),
            WinitKeyCode::F8 => Some(crate::event::KeyCode::F8),
            WinitKeyCode::F9 => Some(crate::event::KeyCode::F9),
            WinitKeyCode::F10 => Some(crate::event::KeyCode::F10),
            WinitKeyCode::F11 => Some(crate::event::KeyCode::F11),
            WinitKeyCode::F12 => Some(crate::event::KeyCode::F12),
            _ => None,
        }
    }
    
    pub fn shutdown(&mut self) {
        log::info!("Shutting down...");
        
        self.running = false;
        
        // 关闭所有服务
        self.service_container.shutdown_all();
        
        log::info!("Shutdown complete");
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // 初始化日志
    env_logger::init();
    
    let mut app = Application::new().await?;
    
    // 设置panic hook
    std::panic::set_hook(Box::new(|panic_info| {
        log::error!("Panic occurred: {}", panic_info);
    }));
    
    // 初始化应用程序
    if let Err(e) = app.initialize().await {
        log::error!("Failed to initialize application: {}", e);
        return Err(e);
    }
    
    // 关闭应用程序
    app.shutdown();
    
    Ok(())
}