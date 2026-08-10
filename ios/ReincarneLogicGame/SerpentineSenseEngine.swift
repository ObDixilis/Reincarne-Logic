import Combine
import Foundation

enum SenseChannel: String, CaseIterable, Identifiable {
    case coilInstinct
    case auraSight
    case aetherwareOracle
    case hexEcho

    var id: String { rawValue }

    var title: String {
        switch self {
        case .coilInstinct: return "Coil Instinct"
        case .auraSight: return "Aura Sight"
        case .aetherwareOracle: return "Aetherware Oracle"
        case .hexEcho: return "Hex Echo"
        }
    }

    var glyph: String {
        switch self {
        case .coilInstinct: return "〰"
        case .auraSight: return "◉"
        case .aetherwareOracle: return "⌬"
        case .hexEcho: return "⌁"
        }
    }

    var toneFrequency: Double {
        switch self {
        case .coilInstinct: return 180
        case .auraSight: return 260
        case .aetherwareOracle: return 420
        case .hexEcho: return 135
        }
    }
}

enum SerpentineResponse: String, CaseIterable, Identifiable {
    case flow
    case gaze
    case sever
    case ward
    case rewrite

    var id: String { rawValue }

    var title: String { rawValue.capitalized }

    var glyph: String {
        switch self {
        case .flow: return "≈"
        case .gaze: return "◉"
        case .sever: return "╱"
        case .ward: return "⬡"
        case .rewrite: return "⌘"
        }
    }

    var instruction: String {
        switch self {
        case .flow: return "Redirect momentum"
        case .gaze: return "Lock hostile intent"
        case .sever: return "Cut the causal strand"
        case .ward: return "Ground the aether field"
        case .rewrite: return "Counter-command the mesh"
        }
    }
}

enum ThreatFamily: String, CaseIterable, Identifiable {
    case kineticFracture
    case auraPredation
    case hexWeave
    case aetherSurge
    case cyberIntrusion

    var id: String { rawValue }

    var title: String {
        switch self {
        case .kineticFracture: return "Kinetic Fracture"
        case .auraPredation: return "Aura Predation"
        case .hexWeave: return "Hex Weave"
        case .aetherSurge: return "Aether Surge"
        case .cyberIntrusion: return "Cyber Intrusion"
        }
    }

    var glyph: String {
        switch self {
        case .kineticFracture: return "◈"
        case .auraPredation: return "◉"
        case .hexWeave: return "⌁"
        case .aetherSurge: return "✦"
        case .cyberIntrusion: return "⌬"
        }
    }

    var dominantChannel: SenseChannel {
        switch self {
        case .kineticFracture: return .coilInstinct
        case .auraPredation: return .auraSight
        case .hexWeave: return .hexEcho
        case .aetherSurge: return .auraSight
        case .cyberIntrusion: return .aetherwareOracle
        }
    }

    var correctResponse: SerpentineResponse {
        switch self {
        case .kineticFracture: return .flow
        case .auraPredation: return .gaze
        case .hexWeave: return .sever
        case .aetherSurge: return .ward
        case .cyberIntrusion: return .rewrite
        }
    }
}

enum ThreatDirection: String, CaseIterable, Identifiable {
    case north
    case northEast
    case east
    case southEast
    case south
    case southWest
    case west
    case northWest

    var id: String { rawValue }

    var shortLabel: String {
        switch self {
        case .north: return "N"
        case .northEast: return "NE"
        case .east: return "E"
        case .southEast: return "SE"
        case .south: return "S"
        case .southWest: return "SW"
        case .west: return "W"
        case .northWest: return "NW"
        }
    }

    var spokenLabel: String {
        switch self {
        case .north: return "north"
        case .northEast: return "northeast"
        case .east: return "east"
        case .southEast: return "southeast"
        case .south: return "south"
        case .southWest: return "southwest"
        case .west: return "west"
        case .northWest: return "northwest"
        }
    }

    /// SwiftUI screen-space angle: north begins at -90 degrees.
    var angleRadians: Double {
        switch self {
        case .north: return -.pi / 2
        case .northEast: return -.pi / 4
        case .east: return 0
        case .southEast: return .pi / 4
        case .south: return .pi / 2
        case .southWest: return 3 * .pi / 4
        case .west: return .pi
        case .northWest: return -3 * .pi / 4
        }
    }

    /// Constant-power stereo pan. Vertical cues remain centered.
    var stereoPan: Double {
        switch self {
        case .east, .northEast, .southEast: return 0.82
        case .west, .northWest, .southWest: return -0.82
        case .north, .south: return 0
        }
    }
}

struct SerpentineThreat: Identifiable, Equatable {
    let id = UUID()
    let family: ThreatFamily
    let direction: ThreatDirection
    let leadSeconds: Double
    let severity: Double
    let confidence: Double
    let ambiguity: Double

    var channel: SenseChannel { family.dominantChannel }
}

struct SerpentineSenseTuning {
    var targetDecisionSeconds = 0.90
    var cueLatencySeconds = 0.17
    var inputLatencySeconds = 0.08
    var minimumTimeScale = 0.10
    var minimumAssistConfidence = 0.45
    var fullAssistConfidence = 0.85
    var ambiguityBudgetMultiplier = 0.35
    var ambiguityAssistPenalty = 0.35
    var reserveCostRate = 7.5
    var maximumReserve = 100.0
}

struct SerpentineSenseDecision: Equatable {
    let requestedTimeScale: Double
    let timeScale: Double
    let realWindowSeconds: Double
    let usableResponseSeconds: Double
    let requestedDecisionSeconds: Double
    let assistWeight: Double
    let reserveCost: Double
    let reserveLimited: Bool
    let whisperOnly: Bool
    let targetMet: Bool
    let unavoidableAtMinimumScale: Bool
}

enum SerpentineSenseMath {
    static func evaluate(
        threat: SerpentineThreat,
        reserve: Double,
        tuning: SerpentineSenseTuning = .init()
    ) -> SerpentineSenseDecision {
        let decisionBudget = tuning.targetDecisionSeconds
            * (1 + threat.ambiguity * tuning.ambiguityBudgetMultiplier)
        let totalBudget = decisionBudget
            + tuning.cueLatencySeconds
            + tuning.inputLatencySeconds
        let requestedScale = clamp(
            threat.leadSeconds / totalBudget,
            tuning.minimumTimeScale,
            1
        )
        let confidenceWeight = smoothstep(
            tuning.minimumAssistConfidence,
            tuning.fullAssistConfidence,
            threat.confidence
        )
        let assistWeight = clamp(
            confidenceWeight
                * threat.severity
                * (1 - threat.ambiguity * tuning.ambiguityAssistPenalty),
            0,
            1
        )
        let desiredScale = 1 - (1 - requestedScale) * assistWeight
        let availableReserve = clamp(reserve, 0, tuning.maximumReserve)
        let limited = reserveLimitedScale(
            desiredScale: desiredScale,
            reserve: availableReserve,
            threat: threat,
            tuning: tuning
        )
        let realWindow = threat.leadSeconds / limited.scale
        let usableWindow = max(
            0,
            realWindow - tuning.cueLatencySeconds - tuning.inputLatencySeconds
        )
        let maximumUsableWindow = max(
            0,
            threat.leadSeconds / tuning.minimumTimeScale
                - tuning.cueLatencySeconds
                - tuning.inputLatencySeconds
        )

        return SerpentineSenseDecision(
            requestedTimeScale: requestedScale,
            timeScale: limited.scale,
            realWindowSeconds: realWindow,
            usableResponseSeconds: usableWindow,
            requestedDecisionSeconds: decisionBudget,
            assistWeight: assistWeight,
            reserveCost: limited.cost,
            reserveLimited: limited.isLimited,
            whisperOnly: assistWeight <= 0.000_000_001,
            targetMet: usableWindow + 0.000_000_001 >= decisionBudget,
            unavoidableAtMinimumScale:
                maximumUsableWindow + 0.000_000_001 < decisionBudget
        )
    }

    private static func reserveLimitedScale(
        desiredScale: Double,
        reserve: Double,
        threat: SerpentineThreat,
        tuning: SerpentineSenseTuning
    ) -> (scale: Double, cost: Double, isLimited: Bool) {
        let desiredCost = reserveCost(
            leadSeconds: threat.leadSeconds,
            timeScale: desiredScale,
            severity: threat.severity,
            tuning: tuning
        )
        guard desiredCost > reserve + 0.000_000_001 else {
            return (desiredScale, desiredCost, false)
        }
        guard reserve > 0 else {
            return (1, 0, true)
        }

        var lower = desiredScale
        var upper = 1.0
        for _ in 0..<64 {
            let candidate = (lower + upper) / 2
            let candidateCost = reserveCost(
                leadSeconds: threat.leadSeconds,
                timeScale: candidate,
                severity: threat.severity,
                tuning: tuning
            )
            if candidateCost > reserve {
                lower = candidate
            } else {
                upper = candidate
            }
        }
        return (
            upper,
            min(
                reserve,
                reserveCost(
                    leadSeconds: threat.leadSeconds,
                    timeScale: upper,
                    severity: threat.severity,
                    tuning: tuning
                )
            ),
            true
        )
    }

    private static func reserveCost(
        leadSeconds: Double,
        timeScale: Double,
        severity: Double,
        tuning: SerpentineSenseTuning
    ) -> Double {
        let realWindow = leadSeconds / max(timeScale, 0.000_001)
        return (
            tuning.reserveCostRate
                * (1 - timeScale)
                * realWindow
                * (0.5 + 0.5 * severity)
        )
    }

    private static func smoothstep(
        _ edge0: Double,
        _ edge1: Double,
        _ value: Double
    ) -> Double {
        let normalized = clamp((value - edge0) / (edge1 - edge0), 0, 1)
        return normalized * normalized * (3 - 2 * normalized)
    }

    private static func clamp(
        _ value: Double,
        _ lower: Double,
        _ upper: Double
    ) -> Double {
        max(lower, min(value, upper))
    }
}

@MainActor
final class SerpentineSenseEngine: ObservableObject {
    enum Phase: Equatable {
        case dormant
        case waiting
        case sensing
        case crownFlare
        case resolved
        case ruptured
        case ignored
    }

    @Published private(set) var phase: Phase = .dormant
    @Published private(set) var activeThreat: SerpentineThreat?
    @Published private(set) var decision: SerpentineSenseDecision?
    @Published private(set) var selectedDirection: ThreatDirection?
    @Published private(set) var selectedResponse: SerpentineResponse?
    @Published private(set) var timeRemaining = 0.0
    @Published private(set) var reserve = 100.0
    @Published private(set) var score = 0
    @Published private(set) var coilStreak = 0
    @Published private(set) var statusMessage =
        "Wake the crown. Read pressure, aura, code, and hex."

    let tuning = SerpentineSenseTuning()

    private var countdownTimer: Timer?
    private var launchTimer: Timer?
    private var lastTick: Date?

    var isThreatActive: Bool {
        phase == .sensing || phase == .crownFlare
    }

    var canSelectResponse: Bool {
        guard let threat = activeThreat else { return false }
        return isThreatActive && selectedDirection == threat.direction
    }

    var primaryActionTitle: String {
        switch phase {
        case .dormant: return "Wake the Crown"
        case .waiting: return "Listening…"
        case .sensing, .crownFlare: return "Threat in Motion"
        case .resolved, .ruptured, .ignored: return "Read Next Omen"
        }
    }

    func primaryAction() {
        switch phase {
        case .dormant:
            beginCalibration()
        case .resolved, .ruptured, .ignored:
            scheduleNextThreat(after: 0.35)
        case .waiting, .sensing, .crownFlare:
            break
        }
    }

    func beginCalibration() {
        invalidateTimers()
        score = 0
        coilStreak = 0
        reserve = tuning.maximumReserve
        statusMessage = "The crown opens across eight directions."
        scheduleNextThreat(after: 0.55)
    }

    func choose(direction: ThreatDirection) {
        guard isThreatActive, let threat = activeThreat else { return }
        selectedDirection = direction
        guard direction == threat.direction else {
            finish(
                success: false,
                message: "False coil. The omen arrived from \(threat.direction.spokenLabel)."
            )
            return
        }
        statusMessage =
            "Source locked: \(direction.spokenLabel). Choose how the Gorgon answers."
    }

    func choose(response: SerpentineResponse) {
        guard canSelectResponse, let threat = activeThreat else { return }
        selectedResponse = response
        guard response == threat.family.correctResponse else {
            finish(
                success: false,
                message:
                    "The channel crossed. \(threat.family.correctResponse.title) was the clean answer."
            )
            return
        }
        finish(
            success: true,
            message:
                "\(response.title) braided through \(threat.channel.title). Omen resolved."
        )
    }

    func ignoreCurrentThreat() {
        guard isThreatActive else { return }
        invalidateTimers()
        coilStreak = max(0, coilStreak - 1)
        reserve = min(tuning.maximumReserve, reserve + 1)
        phase = .ignored
        statusMessage = "Omen released. You kept agency—and accepted its consequence."
    }

    func pause() {
        invalidateTimers()
        activeThreat = nil
        decision = nil
        selectedDirection = nil
        selectedResponse = nil
        timeRemaining = 0
        phase = .dormant
        statusMessage = "Wake the crown. Read pressure, aura, code, and hex."
    }

    private func scheduleNextThreat(after delay: TimeInterval) {
        invalidateTimers()
        activeThreat = nil
        decision = nil
        selectedDirection = nil
        selectedResponse = nil
        timeRemaining = 0
        phase = .waiting
        statusMessage = "Coils listening across the aether…"

        launchTimer = Timer.scheduledTimer(withTimeInterval: delay, repeats: false) {
            [weak self] _ in
            Task { @MainActor [weak self] in
                self?.launchThreat()
            }
        }
    }

    private func launchThreat() {
        let threat = makeThreat()
        let senseDecision = SerpentineSenseMath.evaluate(
            threat: threat,
            reserve: reserve,
            tuning: tuning
        )
        activeThreat = threat
        decision = senseDecision
        selectedDirection = nil
        selectedResponse = nil
        timeRemaining = threat.leadSeconds
        reserve = max(0, reserve - senseDecision.reserveCost)
        phase = senseDecision.timeScale < 0.98 ? .crownFlare : .sensing

        if senseDecision.whisperOnly {
            statusMessage =
                "Whisper only: uncertain \(threat.channel.title.lowercased()) signal."
        } else if senseDecision.unavoidableAtMinimumScale {
            statusMessage = "Late prophecy. Choose now—the crown cannot make enough time."
        } else {
            statusMessage =
                "\(threat.channel.title) flares from \(threat.direction.spokenLabel)."
        }

        lastTick = Date()
        let timer = Timer(timeInterval: 0.05, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.tick()
            }
        }
        countdownTimer = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    private func tick() {
        guard isThreatActive, let decision else { return }
        let now = Date()
        let realDelta = min(0.20, now.timeIntervalSince(lastTick ?? now))
        lastTick = now
        timeRemaining = max(0, timeRemaining - realDelta * decision.timeScale)
        if timeRemaining <= 0 {
            finish(success: false, message: "The omen crossed the threshold unanswered.")
        }
    }

    private func finish(success: Bool, message: String) {
        guard isThreatActive, let threat = activeThreat else { return }
        invalidateTimers()
        if success {
            coilStreak += 1
            let remainingRatio = threat.leadSeconds > 0
                ? timeRemaining / threat.leadSeconds
                : 0
            let base = Int((threat.severity * 100).rounded())
            let velocity = Int((max(0, remainingRatio) * 50).rounded())
            score += base + velocity + coilStreak * 10
            reserve = min(tuning.maximumReserve, reserve + 3.5)
            phase = .resolved
        } else {
            coilStreak = 0
            reserve = min(tuning.maximumReserve, reserve + 1.5)
            phase = .ruptured
        }
        statusMessage = message
    }

    private func makeThreat() -> SerpentineThreat {
        let family = ThreatFamily.allCases.randomElement() ?? .kineticFracture
        let direction = ThreatDirection.allCases.randomElement() ?? .north
        let leadOptions = [0.24, 0.34, 0.48, 0.68, 0.95, 1.25, 1.60]
        return SerpentineThreat(
            family: family,
            direction: direction,
            leadSeconds: leadOptions.randomElement() ?? 0.68,
            severity: Double.random(in: 0.58...1.0),
            confidence: Double.random(in: 0.36...1.0),
            ambiguity: Double.random(in: 0...0.38)
        )
    }

    private func invalidateTimers() {
        countdownTimer?.invalidate()
        launchTimer?.invalidate()
        countdownTimer = nil
        launchTimer = nil
        lastTick = nil
    }
}
