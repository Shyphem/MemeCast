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

/// Affiche ou masque la fenêtre de réglages.
#[tauri::command]
fn toggle_settings(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("settings") {
        if win.is_visible().unwrap_or(false) {
            let _ = win.hide();
        } else {
            let _ = win.show();
            let _ = win.set_focus();
        }
    }
}

/// Minimise la fenêtre de réglages.
#[tauri::command]
fn minimize_settings(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("settings") {
        let _ = win.minimize();
    }
}

/// Quitte l'application complètement.
#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    app.exit(0);
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(tauri_plugin_autostart::MacosLauncher::LaunchAgent, None))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            set_click_through,
            toggle_settings,
            minimize_settings,
            quit_app,
        ])
        .setup(|app| {
            // --- Overlay : activer click-through au démarrage ---
            if let Some(overlay) = app.get_webview_window("overlay") {
                let _ = overlay.set_ignore_cursor_events(true);
            }

            // --- System Tray ---
            let show_item = MenuItem::with_id(app, "show", "⚙️ Réglages", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "❌ Quitter", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("MemeCast")
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(win) = app.get_webview_window("settings") {
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

            // Masquer au lieu de fermer quand on clique sur X (settings)
            if let Some(settings_win) = app.get_webview_window("settings") {
                let settings_win_clone = settings_win.clone();
                settings_win.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = settings_win_clone.hide();
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Erreur au lancement de MemeCast");
}
