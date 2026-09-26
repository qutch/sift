//
//  SettingsView.swift
//  sift-frontend
//

import AppKit
import SwiftUI

struct SettingsView: View {
    let folders: FolderStore
    let indexingService: IndexingService

    @State private var selection: AccessibleFolder.ID?

    @State private var status: IndexingStatus?

    @State private var showingClearConfirmation = false
    @State private var isClearing = false
    @State private var clearError: String?

    @State private var showingFilesSheet = false

    init(folders: FolderStore, indexingService: IndexingService = IndexingService()) {
        self.folders = folders
        self.indexingService = indexingService
    }

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

            if let status, status.isProcessing {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Indexing files… (\(status.filesParsed)/\(status.totalFiles))")
                        .foregroundStyle(.secondary)
                }
            }

            Divider()

            Text("Maintenance")
                .font(.headline)

            HStack {
                Button("View Processed Files…") {
                    showingFilesSheet = true
                }

                Spacer()

                Button("Clear All Data…", role: .destructive) {
                    showingClearConfirmation = true
                }
                .disabled(isClearing)
            }

            if let clearError {
                Text(clearError)
                    .foregroundStyle(.red)
                    .font(.caption)
            }
        }
        .padding(20)
        .frame(width: 480, height: 420)
        .task {
            while !Task.isCancelled {
                await refreshStatus()
                try? await Task.sleep(for: .seconds(1))
            }
        }
        .confirmationDialog(
            "Clear all folders and remove every indexed file?",
            isPresented: $showingClearConfirmation,
            titleVisibility: .visible
        ) {
            Button("Clear All Data", role: .destructive) {
                Task { await clearAllData() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This removes Sift's access to all folders and deletes everything in the search index. This can't be undone.")
        }
        .sheet(isPresented: $showingFilesSheet) {
            ProcessedFilesView(indexingService: indexingService)
        }
    }

    private func refreshStatus() async {
        status = try? await indexingService.status()
    }

    private func clearAllData() async {
        isClearing = true
        clearError = nil
        defer { isClearing = false }

        do {
            try await indexingService.clearDatabase()
            folders.removeAllFolders()
        } catch {
            clearError = error.localizedDescription
        }
    }
}

/// Sheet listing every file the backend has indexed so far.
private struct ProcessedFilesView: View {
    let indexingService: IndexingService

    @Environment(\.dismiss) private var dismiss
    @State private var files: [IndexedFile] = []
    @State private var isLoading = true
    @State private var loadError: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Processed Files")
                    .font(.headline)
                Spacer()
                Button("Done") { dismiss() }
            }

            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let loadError {
                Text(loadError)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if files.isEmpty {
                Text("No files indexed yet")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(files) { file in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(file.fileName)
                        Text(file.filePath)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                }
            }
        }
        .padding(20)
        .frame(width: 480, height: 360)
        .task {
            await loadFiles()
        }
    }

    private func loadFiles() async {
        isLoading = true
        loadError = nil
        do {
            files = try await indexingService.processedFiles()
        } catch {
            loadError = error.localizedDescription
        }
        isLoading = false
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
