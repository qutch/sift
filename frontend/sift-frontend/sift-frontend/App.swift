//
//  sift_frontendApp.swift
//  sift-frontend
//
//  Created by  Hutch Turner on 9/25/26.
//

import SwiftUI

@main
struct sift_frontendApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        // Sift lives in the menu bar; the search panel is summoned with option+space.
        MenuBarExtra("Sift", systemImage: "magnifyingglass") {
            Button("Show Sift") { appDelegate.panel?.show() }
            Button("Settings…") { appDelegate.settings?.show() }
                .keyboardShortcut(",")
            Divider()
            Button("Quit Sift") { NSApp.terminate(nil) }
                .keyboardShortcut("q")
        }
    }
}
