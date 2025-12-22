import Foundation

final class GameEngine: ObservableObject {
    enum Phase {
        case ready
        case showing
        case input
        case success
        case failure
    }

    struct Tile: Identifiable, Equatable {
        let id = UUID()
        let symbol: String
        let meaning: String
        let colorName: String
    }

    @Published private(set) var phase: Phase = .ready
    @Published private(set) var sequence: [Tile] = []
    @Published private(set) var input: [Tile] = []
    @Published private(set) var showTile: Tile?
    @Published private(set) var statusMessage = "Tap Start to begin."
    @Published private(set) var score = 0
    @Published private(set) var level = 1
    @Published private(set) var timeRemaining: Double = 0

    let tiles: [Tile] = [
        Tile(symbol: "🔺", meaning: "Focus", colorName: "Red"),
        Tile(symbol: "⚡", meaning: "Speed", colorName: "Yellow"),
        Tile(symbol: "🌊", meaning: "Flow", colorName: "Blue"),
        Tile(symbol: "🧠", meaning: "Meaning", colorName: "Purple"),
        Tile(symbol: "🟢", meaning: "Growth", colorName: "Green"),
        Tile(symbol: "✨", meaning: "Insight", colorName: "Mint")
    ]

    private var showTimer: Timer?
    private var inputTimer: Timer?
    private var showIndex = 0
    private var inputStart: Date?

    func startGame() {
        score = 0
        level = 1
        nextRound()
    }

    func nextRound() {
        input.removeAll()
        sequence = generateSequence()
        showIndex = 0
        statusMessage = "Watch the pattern, then stack the meanings."
        beginShowSequence()
    }

    func resetAfterFailure() {
        score = 0
        level = 1
        input.removeAll()
        sequence.removeAll()
        showTile = nil
        timeRemaining = 0
        statusMessage = "Tap Start to try again."
        phase = .ready
    }

    func handleTap(tile: Tile) {
        guard phase == .input else { return }
        if inputStart == nil {
            inputStart = Date()
        }
        guard input.count < sequence.count else { return }
        let expected = sequence[input.count]
        if tile == expected {
            input.append(tile)
            if input.count == sequence.count {
                finishRound(success: true)
            }
        } else {
            finishRound(success: false)
        }
    }

    private func generateSequence() -> [Tile] {
        let length = min(2 + level, 6)
        return (0..<length).map { _ in tiles.randomElement() ?? tiles[0] }
    }

    private func beginShowSequence() {
        invalidateTimers()
        phase = .showing
        showTile = nil
        showIndex = 0
        showTimer = Timer.scheduledTimer(withTimeInterval: 0.85, repeats: true) { [weak self] timer in
            guard let self else {
                timer.invalidate()
                return
            }
            if self.showIndex < self.sequence.count {
                self.showTile = self.sequence[self.showIndex]
                self.showIndex += 1
            } else {
                timer.invalidate()
                self.showTile = nil
                self.beginInputPhase()
            }
        }
    }

    private func beginInputPhase() {
        phase = .input
        inputStart = nil
        timeRemaining = Double(sequence.count) * 3.5
        statusMessage = "Repeat the pattern fast to earn velocity bonus."
        inputTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] timer in
            guard let self else {
                timer.invalidate()
                return
            }
            self.timeRemaining = max(0, self.timeRemaining - 0.1)
            if self.timeRemaining <= 0 {
                timer.invalidate()
                self.finishRound(success: false)
            }
        }
    }

    private func finishRound(success: Bool) {
        invalidateTimers()
        if success {
            let timeLimit = Double(sequence.count) * 3.5
            let elapsed = Date().timeIntervalSince(inputStart ?? Date())
            let velocityBonus = max(0, Int((timeLimit - elapsed) * 10))
            score += (sequence.count * 10) + velocityBonus
            level += 1
            statusMessage = "Great stack! +\(velocityBonus) velocity bonus."
            phase = .success
        } else {
            statusMessage = "Pattern break. Reset and try again."
            phase = .failure
        }
    }

    private func invalidateTimers() {
        showTimer?.invalidate()
        inputTimer?.invalidate()
        showTimer = nil
        inputTimer = nil
    }
}
