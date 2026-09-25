//
//  SearchPanel.swift
//  sift-frontend
//
//  The floating, borderless window that hosts the search UI.
//

import AppKit
import SwiftUI

final class SearchPanel: NSPanel {
    init(contentRect: NSRect) {
        super.init(contentRect: contentRect,
                   styleMask: [.borderless, .nonactivatingPanel, .fullSizeContentView],
                   backing: .buffered,
                   defer: false)
        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        isMovableByWindowBackground = true
        isOpaque = false
        backgroundColor = .clear
        hasShadow = true
        hidesOnDeactivate = false
    }

    // Borderless panels can't take keyboard focus by default.
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }

    // Escape closes the panel.
    override func cancelOperation(_ sender: Any?) {
        (delegate as? SearchPanelController)?.hide()
    }
}

final class SearchPanelController: NSObject, NSWindowDelegate {
    static let size = NSSize(width: 640, height: 420)

    private let panel: SearchPanel
    private let model = SearchModel(service: APISearchService())
    private let folders: FolderStore
    private let onOpenSettings: () -> Void
    // The open panel takes key focus while it's up; don't treat that as
    // clicking away from the search panel.
    private var isChoosingFolders = false

    init(folders: FolderStore, onOpenSettings: @escaping () -> Void) {
        self.folders = folders
        self.onOpenSettings = onOpenSettings
        panel = SearchPanel(contentRect: NSRect(origin: .zero, size: Self.size))
        super.init()
        panel.delegate = self

        let view = SearchView(model: model,
                              folders: folders,
                              onDismiss: { [weak self] in self?.hide() },
                              onChooseFolders: { [weak self] in self?.chooseFolders() },
                              onOpenSettings: { [weak self] in self?.openSettings() })
        let hosting = NSHostingView(rootView: view)
        hosting.sizingOptions = []
        panel.contentView = hosting
    }

    var isVisible: Bool { panel.isVisible }

    func toggle() {
        isVisible ? hide() : show()
    }

    func show() {
        model.reset()
        position()
        NSApp.activate()
        panel.makeKeyAndOrderFront(nil)
    }

    func hide() {
        guard panel.isVisible else { return }
        panel.orderOut(nil)
        // Hand focus back to whatever app was frontmost before, unless one of
        // Sift's own windows (e.g. Settings) is still open.
        let otherWindowOpen = NSApp.windows.contains { $0 !== panel && $0.isVisible && $0.styleMask.contains(.titled) }
        if !otherWindowOpen {
            NSApp.hide(nil)
        }
    }

    private func chooseFolders() {
        isChoosingFolders = true
        folders.chooseFolders()
        isChoosingFolders = false
        model.reset()
        panel.makeKeyAndOrderFront(nil)
    }

    private func openSettings() {
        panel.orderOut(nil)
        onOpenSettings()
    }

    // Center horizontally, slightly above center vertically (Spotlight-style).
    private func position() {
        let screen = NSScreen.screens.first { $0.frame.contains(NSEvent.mouseLocation) } ?? NSScreen.main
        guard let visible = screen?.visibleFrame else { return }
        let origin = NSPoint(x: visible.midX - Self.size.width / 2,
                             y: visible.minY + visible.height * 0.62 - Self.size.height / 2)
        panel.setFrame(NSRect(origin: origin, size: Self.size), display: false)
    }

    // Clicking outside the panel dismisses it.
    func windowDidResignKey(_ notification: Notification) {
        guard !isChoosingFolders else { return }
        hide()
    }
}
