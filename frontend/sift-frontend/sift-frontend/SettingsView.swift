//
//  SettingsView.swift
//  sift-frontend
//

import AppKit
import SwiftUI

struct SettingsView: View {
    let folders: FolderStore
    @State private var selection: AccessibleFolder.ID?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Folders")
                .font(.headline)
            Text("Sift can only search files inside these folders.")
                .foregroundStyle(.secondary)

            List(folders.folders, selection: $selection) { folder in
                HStack(spacing: 8) {
                    Image(nsImage: NSWorkspace.shared.icon(forFile: folder.url.path))
                        .resizable()
                        .frame(width: 20, height: 20)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(folder.name)
                        Text(folder.url.path)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                }
            }
            .overlay {
                if !folders.hasFolders {
                    Text("No folders yet")
                        .foregroundStyle(.secondary)
                }
            }

            HStack {
                Button("Add Folder…") { folders.chooseFolders() }
                Button("Remove") {
                    guard let folder = folders.folders.first(where: { $0.id == selection }) else { return }
                    folders.remove(folder)
                    selection = nil
                }
                .disabled(selection == nil)
            }
        }
        .padding(20)
        .frame(width: 480, height: 360)
    }
}

/// A plain AppKit window rather than a SwiftUI `Settings` scene, so it can be
/// opened reliably from the menu bar and the search panel in an accessory app.
final class SettingsWindowController {
    private let folders: FolderStore
    private var window: NSWindow?

    init(folders: FolderStore) {
        self.folders = folders
    }

    func show() {
        if window == nil {
            let window = NSWindow(contentViewController: NSHostingController(rootView: SettingsView(folders: folders)))
            window.title = "Sift Settings"
            window.styleMask = [.titled, .closable]
            window.isReleasedWhenClosed = false
            window.center()
            self.window = window
        }
        NSApp.activate()
        window?.makeKeyAndOrderFront(nil)
    }
}

#Preview {
    SettingsView(folders: FolderStore())
}
