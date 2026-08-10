import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            PatternVelocityView()
                .tabItem {
                    Label("Pattern", systemImage: "square.grid.3x3.fill")
                }

            SerpentineSenseView()
                .tabItem {
                    Label("Serpentine", systemImage: "eye.circle.fill")
                }
        }
        .tint(Color(red: 0.96, green: 0.73, blue: 0.25))
    }
}

private struct PatternVelocityView: View {
    @StateObject private var engine = GameEngine()

    private let columns = [
        GridItem(.flexible(), spacing: 16),
        GridItem(.flexible(), spacing: 16),
        GridItem(.flexible(), spacing: 16)
    ]

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color.black, Color.blue.opacity(0.4)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
            VStack(spacing: 20) {
                VStack(spacing: 8) {
                    Text("Pattern Velocity")
                        .font(.largeTitle.bold())
                        .foregroundColor(.white)
                    Text("Stack meaning, recognize patterns, move fast.")
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.8))
                }

                HStack(spacing: 24) {
                    statCard(title: "Score", value: "\(engine.score)")
                    statCard(title: "Level", value: "\(engine.level)")
                    statCard(
                        title: "Time",
                        value: String(format: "%.1f", engine.timeRemaining)
                    )
                }

                Text(engine.statusMessage)
                    .font(.headline)
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                Group {
                    if engine.phase == .showing, let tile = engine.showTile {
                        VStack(spacing: 12) {
                            Text(tile.symbol)
                                .font(.system(size: 72))
                            Text(tile.meaning.uppercased())
                                .font(.headline)
                                .foregroundColor(.white.opacity(0.8))
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.white.opacity(0.1))
                        .cornerRadius(20)
                    } else {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Meaning Stack")
                                .font(.headline)
                                .foregroundColor(.white)
                            if engine.input.isEmpty {
                                Text("Match the pattern to build your stack.")
                                    .foregroundColor(.white.opacity(0.7))
                            } else {
                                ForEach(engine.input) { tile in
                                    Text("• \(tile.meaning)")
                                        .foregroundColor(.white.opacity(0.8))
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color.white.opacity(0.1))
                        .cornerRadius(20)
                    }
                }

                LazyVGrid(columns: columns, spacing: 16) {
                    ForEach(engine.tiles) { tile in
                        Button {
                            engine.handleTap(tile: tile)
                        } label: {
                            VStack(spacing: 6) {
                                Text(tile.symbol)
                                    .font(.system(size: 36))
                                Text(tile.meaning)
                                    .font(.caption.bold())
                            }
                            .frame(maxWidth: .infinity, minHeight: 80)
                            .padding(8)
                            .background(Color.white.opacity(0.15))
                            .foregroundColor(.white)
                            .cornerRadius(16)
                        }
                        .disabled(engine.phase != .input)
                    }
                }

                Button(action: primaryAction) {
                    Text(primaryActionTitle)
                        .font(.headline)
                        .foregroundColor(.black)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.white)
                        .cornerRadius(16)
                }
            }
            .padding()
        }
    }

    private func statCard(title: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundColor(.white.opacity(0.7))
            Text(value)
                .font(.headline.bold())
                .foregroundColor(.white)
        }
        .frame(maxWidth: .infinity)
        .padding(8)
        .background(Color.white.opacity(0.12))
        .cornerRadius(12)
    }

    private var primaryActionTitle: String {
        switch engine.phase {
        case .ready:
            return "Start"
        case .success:
            return "Next Round"
        case .failure:
            return "Reset"
        case .showing, .input:
            return "Focus"
        }
    }

    private func primaryAction() {
        switch engine.phase {
        case .ready:
            engine.startGame()
        case .success:
            engine.nextRound()
        case .failure:
            engine.resetAfterFailure()
        case .showing, .input:
            break
        }
    }
}

#Preview {
    ContentView()
}

