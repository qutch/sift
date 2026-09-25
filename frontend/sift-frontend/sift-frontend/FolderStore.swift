//
//  FolderStore.swift
//  sift-frontend
//
//  The folders the user has given Sift access to. The app is sandboxed, so
//  access comes from the open panel and is kept across launches with
//  security-scoped bookmarks saved in UserDefaults.
//

import AppKit
import Observation
import os

struct AccessibleFolder: Identifiable, Hashable {
    let url: URL
    let bookmark: Data

    var id: String { url.path }
    var name: String { url.lastPathComponent }
}

@Observable
final class FolderStore {
    private(set) var folders: [AccessibleFolder] = []
    var hasFolders: Bool { !folders.isEmpty }

    private static let defaultsKey = "folderBookmarks"
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        restore()
    }

    /// Shows an open panel and adds whichever folders the user picks.
    func chooseFolders() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = true
        panel.prompt = "Give Access"
        panel.message = "Choose the folders you want Sift to search."
        guard panel.runModal() == .OK else { return }

        for url in panel.urls where !folders.contains(where: { $0.id == url.path }) {
            do {
                let bookmark = try Self.makeBookmark(for: url)
                // The open panel already granted access for this launch.
                _ = url.startAccessingSecurityScopedResource()
                folders.append(AccessibleFolder(url: url, bookmark: bookmark))
            } catch {
                Logger().error("Couldn't save access to \(url.path): \(error)")
            }
        }
        save()
    }

    func remove(_ folder: AccessibleFolder) {
        folder.url.stopAccessingSecurityScopedResource()
        folders.removeAll { $0.id == folder.id }
        save()
    }

    // Re-opens access to every saved folder. Folders that were deleted or
    // can no longer be accessed are dropped.
    private func restore() {
        let saved = defaults.array(forKey: Self.defaultsKey) as? [Data] ?? []

        for data in saved {
            var isStale = false
            guard let url = try? URL(resolvingBookmarkData: data, options: .withSecurityScope,
                                     relativeTo: nil, bookmarkDataIsStale: &isStale),
                  url.startAccessingSecurityScopedResource() else { continue }

            // Stale bookmarks (e.g. the folder was moved) still resolve, but
            // need to be recreated so they keep working next launch.
            let bookmark = isStale ? ((try? Self.makeBookmark(for: url)) ?? data) : data
            folders.append(AccessibleFolder(url: url, bookmark: bookmark))
        }
        save()
    }

    private func save() {
        defaults.set(folders.map(\.bookmark), forKey: Self.defaultsKey)
    }

    private static func makeBookmark(for url: URL) throws -> Data {
        try url.bookmarkData(options: [.withSecurityScope, .securityScopeAllowOnlyReadAccess],
                             includingResourceValuesForKeys: nil, relativeTo: nil)
    }
}
