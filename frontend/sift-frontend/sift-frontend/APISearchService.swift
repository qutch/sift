//
//  APISearchService.swift
//  sift-frontend
//
//  Talks to the Sift FastAPI backend (backend/app/app.py).
//

import Foundation

enum APISearchError: LocalizedError {
    case badStatus(Int)

    var errorDescription: String? {
        switch self {
        case .badStatus(let code): "Sift backend returned HTTP \(code)"
        }
    }
}

/// One line of the backend's streamed `/search` response (see `Searcher.Search`).
private struct SearchStage: Decodable {
    struct QuickFile: Decodable {
        let filePath: String
        // The summary generated for the file when it was indexed.
        let summary: String?
    }

    let type: String
    let files: [QuickFile]?
    let summary: String?
}

struct APISearchService: SearchService {
    var baseURL = URL(string: "http://127.0.0.1:8000")!
    var numFiles = 5

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        // The summary runs on a local LLM, so the stream can go quiet for a
        // while after the results, especially while Ollama loads the model.
        config.timeoutIntervalForRequest = 120
        return URLSession(configuration: config)
    }()

    // TODO: the backend has no recent-files endpoint yet.
    func recentFiles() async -> [FileResult] {
        []
    }

    // Cancelling the consuming task closes the connection. The backend still
    // finishes a summary it has already started.
    func search(_ query: String) -> AsyncThrowingStream<SearchUpdate, Error> {
        var components = URLComponents(url: baseURL.appending(path: "search"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "q", value: query),
            URLQueryItem(name: "numFiles", value: String(numFiles)),
        ]
        let url = components.url!

        return AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let (bytes, response) = try await session.bytes(from: url)
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        throw APISearchError.badStatus(http.statusCode)
                    }

                    for try await line in bytes.lines {
                        let stage = try JSONDecoder().decode(SearchStage.self, from: Data(line.utf8))
                        switch stage.type {
                        case "results":
                            let files = (stage.files ?? []).map { FileResult(path: $0.filePath, summary: $0.summary) }
                            continuation.yield(.results(files))
                        case "summary":
                            if let summary = stage.summary { continuation.yield(.summary(summary)) }
                        default:
                            break
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}
