//
//  AppDelegate.swift
//  sift-frontend
//

import AppKit
import Carbon.HIToolbox

final class AppDelegate: NSObject, NSApplicationDelegate {
    private(set) var panel: SearchPanelController?
    private var hotKey: HotKey?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // No dock icon, like Spotlight/Raycast.
        NSApp.setActivationPolicy(.accessory)

        let panel = SearchPanelController()
        self.panel = panel

        hotKey = HotKey(keyCode: UInt32(kVK_Space), modifiers: UInt32(optionKey)) {
            panel.toggle()
        }
    }
}
