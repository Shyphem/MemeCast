// MemeCast — Logique principale Tauri v2
//
// Responsabilités :
//   - Configurer la fenêtre overlay (click-through, always-on-top)
//   - Gérer le system tray (icône + menu)
//   - Exposer des commandes Rust au frontend JavaScript

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager, WindowEvent,
};

/// Active le mode "click-through" sur la fenêtre overlay.
/// Les clics de souris passent à travers la fenêtre.
#[tauri::command]
fn set_click_through(window: tauri::Window, ignore: bool) {
    let _ = window.set_ignore_cursor_events(ignore);
}

/// Retourne la liste des moniteurs disponibles.
#[tauri::command]
fn list_monitors(app: tauri::AppHandle) -> Vec<serde_json::Value> {
    let monitors = app.available_monitors().unwrap_or_default();
    monitors
        .iter()
        .enumerate()
        .map(|(i, m)| {
            let pos = m.position();
            let size = m.size();
            serde_json::json!({
                "index": i,
                "name": m.name().unwrap_or(&format!("Écran {}", i + 1)),
                "width": size.width,
                "height": size.height,
                "x": pos.x,
                "y": pos.y,
            })
        })
        .collect()
}

/// Déplace l'overlay sur le moniteur indiqué par son index.
#[tauri::command]
fn move_overlay_to_monitor(app: tauri::AppHandle, monitor_index: usize) {
    let monitors = app.available_monitors().unwrap_or_default();
    if let Some(monitor) = monitors.get(monitor_index) {
        if let Some(overlay) = app.get_webview_window("overlay") {
            let pos = monitor.position();
            let size = monitor.size();
            let _ = overlay.set_position(tauri::Position::Physical(
                tauri::PhysicalPosition::new(pos.x, pos.y),
            ));
            let _ = overlay.set_size(tauri::Size::Physical(
                tauri::PhysicalSize::new(size.width, size.height),
            ));
        }
    }
}

/// Affiche la fenêtre de setup.
#[tauri::command]
fn show_setup(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("setup") {
        let _ = win.show();
        let _ = win.set_focus();
    }
}

/// Ferme la fenêtre de setup.
#[tauri::command]
fn close_setup(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("setup") {
        let _ = win.hide();
    }
}

/// Quitte l'application complètement.
#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    app.exit(0);
}

/// Désinstalle l'application complètement.
///
/// 1. Désactive l'autostart
/// 2. Crée un script batch qui supprime le dossier d'installation après que l'app quitte
/// 3. Quitte l'application
#[tauri::command]
fn uninstall_self(app: tauri::AppHandle) {
    // 1. Desactiver l'autostart
    {
        use tauri_plugin_autostart::ManagerExt;
        let _ = app.autolaunch().disable();
    }

    // 2. Supprimer le raccourci du menu demarrer
    if let Ok(appdata) = std::env::var("APPDATA") {
        let start_menu = std::path::Path::new(&appdata)
            .join("Microsoft\\Windows\\Start Menu\\Programs\\MemeCast Headless");
        if start_menu.exists() {
            let _ = std::fs::remove_dir_all(&start_menu);
        }
    }

    // 3. Creer un script batch de nettoyage
    if let Ok(exe_path) = std::env::current_exe() {
        let exe_name = exe_path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| "memecast.exe".to_string());

        if let Some(install_dir) = exe_path.parent() {
            let install_dir_str = install_dir.to_string_lossy().to_string();

            // Le script tue le process, attend, puis supprime le dossier
            let batch_content = format!(
                "@echo off\r\n\
                 taskkill /F /IM \"{}\" >nul 2>&1\r\n\
                 timeout /t 5 /nobreak >nul\r\n\
                 rmdir /s /q \"{}\"\r\n\
                 del \"%~f0\"\r\n",
                exe_name,
                install_dir_str
            );

            if let Ok(temp_dir) = std::env::var("TEMP") {
                let bat_path = std::path::Path::new(&temp_dir).join("memecast_uninstall.bat");
                if std::fs::write(&bat_path, &batch_content).is_ok() {
                    use std::os::windows::process::CommandExt;
                    const CREATE_NO_WINDOW: u32 = 0x08000000;

                    let bat_str = bat_path.to_string_lossy().to_string();
                    let _ = std::process::Command::new("cmd.exe")
                        .args(["/c", &bat_str])
                        .creation_flags(CREATE_NO_WINDOW)
                        .spawn();
                }
            }
        }
    }

    // 4. Quitter l'application
    app.exit(0);
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(tauri_plugin_autostart::MacosLauncher::LaunchAgent, None))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            set_click_through,
            list_monitors,
            move_overlay_to_monitor,
            show_setup,
            close_setup,
            quit_app,
            uninstall_self,
        ])
        .setup(|app| {
            // --- Overlay : activer click-through au démarrage ---
            if let Some(overlay) = app.get_webview_window("overlay") {
                let _ = overlay.set_ignore_cursor_events(true);
            }

            use tauri_plugin_autostart::ManagerExt;
            let _ = app.autolaunch().enable();

            // --- System Tray ---
            let show_item = MenuItem::with_id(app, "show", "⚙️ Modifier l'alias", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "❌ Quitter", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("MemeCast")
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(win) = app.get_webview_window("setup") {
                            let _ = win.show();
                            let _ = win.set_focus();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            // Masquer au lieu de fermer quand on clique sur X (setup)
            if let Some(setup_win) = app.get_webview_window("setup") {
                let setup_win_clone = setup_win.clone();
                setup_win.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = setup_win_clone.hide();
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Erreur au lancement de MemeCast");
}
