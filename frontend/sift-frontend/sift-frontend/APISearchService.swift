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

/// Mirrors the backend's `Searcher.SearchAndRank` response.
private struct SearchResponse: Decodable {
    struct RankedFile: Decodable {
        let filePath: String
        // Null when the ranker's output couldn't be parsed.
        let relevance: Int?
        let reason: String?
    }

    let summary: String
    let ranking: [RankedFile]
}

struct APISearchService: SearchService {
    var baseURL = URL(string: "http://127.0.0.1:8000")!
    var numFiles = 5

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        // Each search runs a summary and a ranking pass on a local LLM,
        // so responses can take a while.
        config.timeoutIntervalForRequest = 60
        return URLSession(configuration: config)
    }()

    // TODO: the backend has no recent-files endpoint yet.
    func recentFiles() async -> [FileResult] {
        []
    }

    func search(_ query: String) async throws -> [FileResult] {
        var components = URLComponents(url: baseURL.appending(path: "search"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "q", value: query),
            URLQueryItem(name: "numFiles", value: String(numFiles)),
        ]

        let (data, response) = try await session.data(from: components.url!)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw APISearchError.badStatus(http.statusCode)
        }

        let decoded = try JSONDecoder().decode(SearchResponse.self, from: data)
        return decoded.ranking.map { FileResult(path: $0.filePath, summary: $0.reason) }
    }
}
