//
//  IndexingService.swift
//  sift-frontend
//
//  Tells the Sift FastAPI backend to index a folder (backend/app/app.py's
//  POST /process/{folder_path} endpoint).
//

import Foundation

enum IndexingError: LocalizedError {
    case badStatus(Int)

    var errorDescription: String? {
        switch self {
        case .badStatus(let code): "Sift backend returned HTTP \(code)"
        }
    }
}

/// Mirrors the backend's `Parser.GetStatus` response.
struct IndexingStatus: Decodable {
    let isProcessing: Bool
    let filesParsed: Int
    let totalFiles: Int
}

/// Mirrors a single row of the backend's `sift-metadata` LanceDB table.
struct IndexedFile: Decodable, Identifiable {
    let fileType: String
    let fileName: String
    let filePath: String
    let summary: String
    let size: Int
    let lastOpened: String?
    let lastEdited: String?
    let createdAt: String?

    var id: String { filePath }
}

struct IndexingService {
    var baseURL = URL(string: "http://127.0.0.1:8000")!

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        // Indexing walks the whole folder tree, so give it plenty of time.
        config.timeoutIntervalForRequest = 300
        return URLSession(configuration: config)
    }()

    // `path` is a filesystem path (e.g. "/Users/hutch/Documents"). The '/'s
    // need to stay literal for FastAPI's `{folder_path:path}` converter, so
    // this only percent-encodes what's unsafe within a path component.
    func processFolder(at path: String) async throws {
        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)!
        let encodedPath = path.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? path
        components.percentEncodedPath = "/process" + encodedPath

        var request = URLRequest(url: components.url!)
        request.httpMethod = "POST"

        let (_, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw IndexingError.badStatus(http.statusCode)
        }
    }

    // Current indexing progress, used to drive the settings screen's processing indicator.
    func status() async throws -> IndexingStatus {
        let (data, response) = try await session.data(from: baseURL.appending(path: "status"))
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw IndexingError.badStatus(http.statusCode)
        }
        return try JSONDecoder().decode(IndexingStatus.self, from: data)
    }

    // Metadata for every file indexed so far.
    func processedFiles() async throws -> [IndexedFile] {
        let (data, response) = try await session.data(from: baseURL.appending(path: "files"))
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw IndexingError.badStatus(http.statusCode)
        }
        return try JSONDecoder().decode([IndexedFile].self, from: data)
    }

    // Wipes all indexed vectors and metadata from LanceDB.
    func clearDatabase() async throws {
        var request = URLRequest(url: baseURL.appending(path: "database"))
        request.httpMethod = "DELETE"

        let (_, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw IndexingError.badStatus(http.statusCode)
        }
    }
}
