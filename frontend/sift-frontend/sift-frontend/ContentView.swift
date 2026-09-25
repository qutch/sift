//
//  ContentView.swift
//  sift-frontend
//
//  Created by Hutch Turner on 9/25/26.
//

import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct SearchView: View {
    @Bindable var model: SearchModel
    var onDismiss: () -> Void = {}
    @FocusState private var fieldFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            searchBar
            Divider()
            fileList
        }
        .frame(width: SearchPanelController.size.width, height: SearchPanelController.size.height)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .onChange(of: model.focusToken, initial: true) { fieldFocused = true }
    }

    private var searchBar: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)
            TextField("Search files", text: $model.query)
                .textFieldStyle(.plain)
                .font(.system(size: 20))
                .focused($fieldFocused)
                .onKeyPress(.downArrow) { model.moveSelection(by: 1); return .handled }
                .onKeyPress(.upArrow) { model.moveSelection(by: -1); return .handled }
                .onSubmit {
                    guard let file = model.selectedFile else { return }
                    onDismiss()
                    model.openSelectedFile(query: (file.path as NSString).expandingTildeInPath)
                }
            if model.isSearching {
                ProgressView().controlSize(.small)
            }
        }
        .padding(.horizontal, 16)
        .frame(height: 52)
    }

    private var fileList: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(model.isShowingRecents ? "Recent Files" : "Results")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 16)
                .padding(.top, 8)

            if model.visibleFiles.isEmpty {
                Text(model.isShowingRecents || model.isSearching ? "" : "No matching files")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(model.visibleFiles) { file in
                                FileRow(file: file, isSelected: file.id == model.selection)
                                    .id(file.id)
                                    .onTapGesture { model.selection = file.id }
                                    .simultaneousGesture(TapGesture(count: 2).onEnded { open(file) })
                            }
                        }
                        .padding(.horizontal, 8)
                        .padding(.bottom, 8)
                    }
                    .onChange(of: model.selection) { _, id in
                        if let id { proxy.scrollTo(id) }
                    }
                }
            }
        }
        .frame(maxHeight: .infinity, alignment: .top)
    }

    private func open(_ file: FileResult?) {
        guard let file else { return }
        let url = URL(fileURLWithPath: (file.path as NSString).expandingTildeInPath)
        onDismiss()
        NSWorkspace.shared.open(url)
    }
}

private struct FileRow: View {
    let file: FileResult
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 10) {
            Image(nsImage: NSWorkspace.shared.icon(for: .init(filenameExtension: (file.name as NSString).pathExtension) ?? .data))
                .resizable()
                .frame(width: 24, height: 24)
            VStack(alignment: .leading, spacing: 1) {
                Text(file.name)
                    .lineLimit(1)
                Text(file.summary ?? file.directory)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(isSelected ? Color.accentColor.opacity(0.25) : .clear,
                    in: RoundedRectangle(cornerRadius: 6))
        .contentShape(Rectangle())
    }
}

#Preview {
    SearchView(model: SearchModel(service: MockSearchService()))
}
