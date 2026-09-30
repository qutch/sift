//
//  DataLocationStore.swift
//  sift-frontend
//
//  The folder the user chose for Sift's data (the backend's LanceDB
//  database). The backend does the reading and writing, so the app only
//  needs to remember the path and hand it to the backend.
//

import AppKit
import Observation
import os

@Observable
final class DataLocationStore {
    private(set) var path: String?
    var hasLocation: Bool { path != nil }
    /// Why the last attempt to set a location failed, for the UI to show.
    private(set) var lastError: String?

    private static let defaultsKey = "dataLocationPath"
    private let defaults: UserDefaults
    private let indexingService: IndexingService

    init(defaults: UserDefaults = .standard, indexingService: IndexingService = IndexingService()) {
        self.defaults = defaults
        self.indexingService = indexingService
        path = defaults.string(forKey: Self.defaultsKey)
    }

    /// Re-sends the saved location on launch, in case the backend started
    /// fresh or was last pointed somewhere else.
    func syncWithBackend() {
        guard let path else { return }
        Task {
            do {
                try await indexingService.setDataLocation(path)
            } catch {
                Logger().error("Couldn't send data location to backend: \(error)")
            }
        }
    }

    /// Shows an open panel for the data folder. Returns the chosen folder's
    /// path, or nil if the user cancelled.
    func pickFolder() -> String? {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Store Data Here"
        panel.message = "Choose a folder for Sift to store its search index in."
        guard panel.runModal() == .OK, let url = panel.url else { return nil }
        return url.path
    }

    /// Points the backend at `newPath` and saves it only once the backend
    /// accepts it, so the app never remembers a location the backend isn't using.
    func setLocation(_ newPath: String) async {
        do {
            try await indexingService.setDataLocation(newPath)
            path = newPath
            defaults.set(newPath, forKey: Self.defaultsKey)
            lastError = nil
        } catch {
            lastError = "Couldn't use that folder: \(error.localizedDescription)"
        }
    }
}
