//
//  IndexingStatusMonitor.swift
//  sift-frontend
//
//  Polls the backend's indexing status so the search panel and menu bar
//  icon can both show a live processing indicator.
//

import Foundation
import Observation
import SwiftUI

@Observable
final class IndexingStatusMonitor {
    private(set) var status: IndexingStatus?

    private let service: IndexingService
    private var pollTask: Task<Void, Never>?

    init(service: IndexingService = IndexingService()) {
        self.service = service
    }

    func start() {
        guard pollTask == nil else { return }
        pollTask = Task {
            while !Task.isCancelled {
                status = try? await service.status()
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    func stop() {
        pollTask?.cancel()
        pollTask = nil
    }
}

/// Small one-line indicator: a colored dot plus status text.
/// Gray + "Nothing to process" when idle, orange + "Processing {filename}" while indexing.
struct IndexingStatusIndicator: View {
    let status: IndexingStatus?

    private var isProcessing: Bool { status?.isProcessing ?? false }

    private var label: String {
        guard isProcessing else { return "Nothing to process" }
        if let currentFile = status?.currentFile, !currentFile.isEmpty {
            return "Processing \(currentFile)"
        }
        return "Processing…"
    }

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(isProcessing ? Color.orange : Color.gray)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.middle)
        }
    }
}

#Preview("Processing") {
    IndexingStatusIndicator(status: IndexingStatus(isProcessing: true, filesParsed: 2, totalFiles: 10, currentFile: "report.pdf"))
        .padding()
}

#Preview("Idle") {
    IndexingStatusIndicator(status: IndexingStatus(isProcessing: false, filesParsed: 0, totalFiles: 0, currentFile: nil))
        .padding()
}
