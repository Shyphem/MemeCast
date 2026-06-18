// MemeCast — Point d'entrée Rust (Tauri v2)
// Configure l'app, le system tray, et les commandes Rust ↔ JS.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    memecast::run();
}
