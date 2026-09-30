//
//  SearchModel.swift
//  sift-frontend
//

import Foundation
import Observation
import AppKit

struct FileResult: Identifiable, Hashable {
    var id: String { path }
    let path: String
    var summary: String? = nil

    var name: String { (path as NSString).lastPathComponent }
    var directory: String { (path as NSString).deletingLastPathComponent }
}

/// Searches arrive in stages: quick vector results first, then the slower
/// LLM summary once it finishes.
enum SearchUpdate {
    case results([FileResult])
    case summary(String)
}

protocol SearchService {
    func recentFiles() async -> [FileResult]
    func search(_ query: String) -> AsyncThrowingStream<SearchUpdate, Error>
    /// Asks the backend to load what a search needs while the user is still typing.
    func warmUp() async
}

extension SearchService {
    func warmUp() async {}
}

@Observable
final class SearchModel {
    var query = "" {
        didSet { if query != oldValue { scheduleSearch() } }
    }
    private(set) var results: [FileResult] = []
    private(set) var recents: [FileResult] = []
    /// True until the first (vector search) results arrive.
    private(set) var isSearching = false
    /// True while the summary is still catching up.
    private(set) var isSummarizing = false
    /// LLM summary of the results, once it's ready.
    private(set) var summary: String?
    var selection: FileResult.ID?
    /// Bumped every time the panel is shown so the view can re-focus the field.
    private(set) var focusToken = 0

    var isShowingRecents: Bool { query.trimmingCharacters(in: .whitespaces).isEmpty }
    var visibleFiles: [FileResult] { isShowingRecents ? recents : results }

    private let service: SearchService
    private var searchTask: Task<Void, Never>?

    init(service: SearchService) {
        self.service = service
    }

    func reset() {
        searchTask?.cancel()
        query = ""
        results = []
        summary = nil
        isSearching = false
        isSummarizing = false
        focusToken += 1
        Task { await service.warmUp() }
        Task {
            recents = await service.recentFiles()
            selection = recents.first?.id
        }
    }

    func moveSelection(by offset: Int) {
        let files = visibleFiles
        guard !files.isEmpty else { return }
        let current = files.firstIndex { $0.id == selection } ?? -1
        let next = min(max(current + offset, 0), files.count - 1)
        selection = files[next].id
    }

    var selectedFile: FileResult? {
        visibleFiles.first { $0.id == selection }
    }
    
    func openSelectedFile(query: String) {
        if (selection != nil) {
            // Open the file with NSWorkspace
            NSWorkspace.shared.open(URL(fileURLWithPath: query))
        }
    }
    
    // Debounced so we don't hit the backend on every keystroke. Cancelling
    // the previous search closes its request, so the backend drops its summary.
    private func scheduleSearch() {
        searchTask?.cancel()
        let q = query.trimmingCharacters(in: .whitespaces)
        summary = nil
        isSummarizing = false
        guard !q.isEmpty else {
            results = []
            isSearching = false
            selection = recents.first?.id
            return
        }
        isSearching = true
        searchTask = Task {
            try? await Task.sleep(for: .milliseconds(150))
            guard !Task.isCancelled else { return }
            do {
                for try await update in service.search(q) {
                    guard !Task.isCancelled else { return }
                    apply(update)
                }
            } catch {
                guard !Task.isCancelled else { return }
                // Keep whatever stages already arrived; only a failure before
                // the first results leaves the list empty.
                if isSearching { results = [] }
            }
            guard !Task.isCancelled else { return }
            isSearching = false
            isSummarizing = false
        }
    }

    private func apply(_ update: SearchUpdate) {
        switch update {
        case .results(let files):
            results = files
            selection = files.first?.id
            isSearching = false
            isSummarizing = !files.isEmpty
        case .summary(let text):
            summary = text
        }
    }
}

/// Placeholder data for SwiftUI previews and working on the UI without the backend running.
struct MockSearchService: SearchService {
    private static let files: [FileResult] = [
        FileResult(path: "~/Documents/notes/meeting-notes.md", summary: "Weekly sync notes about the indexing roadmap."),
        FileResult(path: "~/Documents/reports/q3-report.pdf", summary: "Quarterly report covering revenue and hiring."),
        FileResult(path: "~/Desktop/test-folder/recipes.txt", summary: "A collection of pasta and bread recipes."),
        FileResult(path: "~/Dev/sift/backend/app/services/search.py", summary: "Search service that ranks files for a query."),
        FileResult(path: "~/Documents/school/essay-draft.md", summary: "Draft essay on renewable energy policy."),
        FileResult(path: "~/Downloads/lease-agreement.pdf", summary: "Apartment lease agreement and terms."),
        FileResult(path: "~/Documents/notes/reading-list.txt", summary: "Books to read this fall."),
    ]

    func recentFiles() async -> [FileResult] {
        Array(Self.files.prefix(5))
    }

    func search(_ query: String) -> AsyncThrowingStream<SearchUpdate, Error> {
        let terms = query.lowercased().split(separator: " ")
        let matches = Self.files.filter { file in
            let haystack = (file.path + " " + (file.summary ?? "")).lowercased()
            return terms.contains { haystack.contains($0) }
        }
        return AsyncThrowingStream { continuation in
            let task = Task {
                try await Task.sleep(for: .milliseconds(200))
                continuation.yield(.results(matches))
                try await Task.sleep(for: .seconds(1))
                continuation.yield(.summary("\(matches.count) files mention \(query)."))
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}
