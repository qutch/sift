//
//  AppDelegate.swift
//  sift-frontend
//

import AppKit
import Carbon.HIToolbox

final class AppDelegate: NSObject, NSApplicationDelegate {
    let folders = FolderStore()
    private(set) var panel: SearchPanelController?
    private(set) var settings: SettingsWindowController?
    private var hotKey: HotKey?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // No dock icon, like Spotlight/Raycast.
        NSApp.setActivationPolicy(.accessory)

        let settings = SettingsWindowController(folders: folders)
        self.settings = settings

        let panel = SearchPanelController(folders: folders, onOpenSettings: { settings.show() })
        self.panel = panel

        // First launch (or every saved folder is gone): show the panel so the
        // user sees the prompt to choose a folder. Deferred until launch
        // finishes, otherwise the panel loses key during app activation and
        // immediately hides itself.
        if !folders.hasFolders {
            DispatchQueue.main.async { panel.show() }
        }

        hotKey = HotKey(keyCode: UInt32(kVK_Space), modifiers: UInt32(optionKey)) {
            panel.toggle()
        }
    }
}
