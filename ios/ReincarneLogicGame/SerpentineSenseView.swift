import AVFoundation
import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

@MainActor
final class SerpentineCueController: ObservableObject {
    private let audioEngine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var isAudioConfigured = false

    func fire(
        threat: SerpentineThreat,
        decision: SerpentineSenseDecision,
        soundEnabled: Bool,
        hapticsEnabled: Bool
    ) {
        if hapticsEnabled {
            fireHaptic(severity: threat.severity, isCrownFlare: decision.timeScale < 0.98)
        }
        if soundEnabled {
            playDirectionalTone(for: threat)
        }
    }

    private func fireHaptic(severity: Double, isCrownFlare: Bool) {
        #if canImport(UIKit)
        let style: UIImpactFeedbackGenerator.FeedbackStyle = isCrownFlare ? .rigid : .medium
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.prepare()
        generator.impactOccurred(intensity: CGFloat(0.45 + severity * 0.55))
        #endif
    }

    private func configureAudioIfNeeded() throws {
        guard !isAudioConfigured else { return }
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.ambient, mode: .default, options: [.mixWithOthers])
        try session.setActive(true)
        audioEngine.attach(player)
        audioEngine.connect(player, to: audioEngine.mainMixerNode, format: nil)
        audioEngine.prepare()
        try audioEngine.start()
        isAudioConfigured = true
    }

    private func playDirectionalTone(for threat: SerpentineThreat) {
        do {
            try configureAudioIfNeeded()
            if !audioEngine.isRunning {
                try audioEngine.start()
            }
        } catch {
            return
        }

        let sampleRate = 44_100.0
        let duration = 0.16
        let frameCount = AVAudioFrameCount(sampleRate * duration)
        guard
            let format = AVAudioFormat(
                standardFormatWithSampleRate: sampleRate,
                channels: 2
            ),
            let buffer = AVAudioPCMBuffer(
                pcmFormat: format,
                frameCapacity: frameCount
            ),
            let channels = buffer.floatChannelData
        else { return }

        buffer.frameLength = frameCount
        let verticalPitch: Double
        switch threat.direction {
        case .north, .northEast, .northWest:
            verticalPitch = 1.16
        case .south, .southEast, .southWest:
            verticalPitch = 0.86
        case .east, .west:
            verticalPitch = 1.0
        }

        let panAngle = (threat.direction.stereoPan + 1) * .pi / 4
        let leftGain = cos(panAngle)
        let rightGain = sin(panAngle)
        let baseFrequency = threat.channel.toneFrequency * verticalPitch

        for frame in 0..<Int(frameCount) {
            let time = Double(frame) / sampleRate
            let progress = time / duration
            let sweep = threat.channel == .hexEcho
                ? 1.18 - progress * 0.42
                : 0.94 + progress * 0.18
            let attack = min(1, progress / 0.06)
            let decay = pow(max(0, 1 - progress), 2.2)
            let envelope = attack * decay
            let fundamental = sin(2 * .pi * baseFrequency * sweep * time)
            let harmonic = 0.28 * sin(2 * .pi * baseFrequency * 2.01 * time)
            let sample = Float((fundamental + harmonic) * envelope * 0.24)
            channels[0][frame] = sample * Float(leftGain)
            channels[1][frame] = sample * Float(rightGain)
        }

        player.stop()
        player.scheduleBuffer(buffer, at: nil, options: .interrupts)
        player.play()
    }
}

struct SerpentineSenseView: View {
    @StateObject private var engine = SerpentineSenseEngine()
    @StateObject private var cueController = SerpentineCueController()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    @State private var soundEnabled = true
    @State private var hapticsEnabled = true

    private let responseColumns = [
        GridItem(.flexible(), spacing: 10),
        GridItem(.flexible(), spacing: 10)
    ]

    var body: some View {
        ZStack {
            aetherBackground
            ScrollView {
                VStack(spacing: 18) {
                    masthead
                    statRail
                    omenCard
                    compass
                    responseGrid
                    controls
                }
                .padding(.horizontal, 16)
                .padding(.top, 18)
                .padding(.bottom, 30)
            }
        }
        .onChange(of: engine.activeThreat?.id) { _ in
            guard
                let threat = engine.activeThreat,
                let decision = engine.decision
            else { return }
            cueController.fire(
                threat: threat,
                decision: decision,
                soundEnabled: soundEnabled,
                hapticsEnabled: hapticsEnabled
            )
        }
        .onDisappear {
            engine.pause()
        }
    }

    private var aetherBackground: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.025, green: 0.018, blue: 0.055),
                    Color(red: 0.08, green: 0.025, blue: 0.15),
                    Color(red: 0.015, green: 0.12, blue: 0.11)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            RadialGradient(
                colors: [aetherGold.opacity(0.16), .clear],
                center: .topTrailing,
                startRadius: 10,
                endRadius: 340
            )
            .blendMode(.screen)
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .trim(
                        from: 0.06 + CGFloat(index) * 0.05,
                        to: 0.62 + CGFloat(index) * 0.06
                    )
                    .stroke(
                        index.isMultiple(of: 2) ? aetherJade.opacity(0.12) : aetherViolet.opacity(0.13),
                        style: StrokeStyle(lineWidth: 1.2, dash: [3, 12])
                    )
                    .rotationEffect(.degrees(Double(index) * 73))
                    .scaleEffect(0.7 + CGFloat(index) * 0.22)
            }
            .allowsHitTesting(false)
        }
        .ignoresSafeArea()
    }

    private var masthead: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(alignment: .firstTextBaseline) {
                Text("SERPENTINE SENSE")
                    .font(.system(.title, design: .rounded, weight: .black))
                    .tracking(1.4)
                    .foregroundStyle(.white)
                Spacer()
                Text("AETHERCOIL // 01")
                    .font(.caption2.monospaced().bold())
                    .foregroundStyle(aetherGold)
            }
            Text("Afro-Gorgon cognition across aura, sorcery, instinct, and machine prophecy.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.68))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var statRail: some View {
        HStack(spacing: 9) {
            statCell(
                label: "RESERVE",
                value: "\(Int(engine.reserve.rounded()))",
                accent: aetherJade
            )
            statCell(
                label: "COIL",
                value: "×\(engine.coilStreak)",
                accent: aetherViolet
            )
            statCell(
                label: "SCORE",
                value: "\(engine.score)",
                accent: aetherGold
            )
        }
    }

    private func statCell(label: String, value: String, accent: Color) -> some View {
        VStack(spacing: 3) {
            Text(label)
                .font(.caption2.monospaced().bold())
                .foregroundStyle(.white.opacity(0.52))
            Text(value)
                .font(.headline.monospacedDigit().bold())
                .foregroundStyle(accent)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(panelBackground)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(accent.opacity(0.75))
                .frame(height: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
    }

    private var omenCard: some View {
        VStack(alignment: .leading, spacing: 11) {
            HStack {
                if let threat = engine.activeThreat {
                    Text(threat.family.glyph)
                        .font(.title2)
                        .foregroundStyle(aetherGold)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(threat.family.title.uppercased())
                            .font(.caption.monospaced().bold())
                            .foregroundStyle(.white)
                        Text("\(threat.channel.glyph) \(threat.channel.title)")
                            .font(.caption)
                            .foregroundStyle(aetherJade)
                    }
                } else {
                    Text("◉")
                        .font(.title2)
                        .foregroundStyle(aetherViolet)
                    Text("CROWN DORMANT")
                        .font(.caption.monospaced().bold())
                        .foregroundStyle(.white)
                }
                Spacer()
                if let decision = engine.decision {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(String(format: "%.2f× WORLD", decision.timeScale))
                            .font(.caption.monospaced().bold())
                            .foregroundStyle(decision.timeScale < 0.98 ? aetherGold : .white)
                        Text(String(format: "%.0f%% CERTAINTY", (engine.activeThreat?.confidence ?? 0) * 100))
                            .font(.caption2.monospaced())
                            .foregroundStyle(.white.opacity(0.58))
                    }
                }
            }

            Text(engine.statusMessage)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.white.opacity(0.86))
                .fixedSize(horizontal: false, vertical: true)

            if let threat = engine.activeThreat {
                ProgressView(
                    value: engine.timeRemaining,
                    total: max(0.001, threat.leadSeconds)
                )
                .tint(engine.phase == .crownFlare ? aetherGold : aetherJade)
                .accessibilityLabel("Threat time remaining")
                .accessibilityValue(String(format: "%.2f seconds", engine.timeRemaining))
            }
        }
        .padding(14)
        .background(panelBackground)
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(aetherViolet.opacity(0.28), lineWidth: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var compass: some View {
        GeometryReader { proxy in
            let side = min(proxy.size.width, proxy.size.height)
            let center = CGPoint(x: proxy.size.width / 2, y: proxy.size.height / 2)
            let radius = side * 0.39

            ZStack {
                Circle()
                    .stroke(aetherJade.opacity(0.15), lineWidth: 1)
                    .frame(width: side * 0.78, height: side * 0.78)
                Circle()
                    .stroke(
                        aetherViolet.opacity(0.32),
                        style: StrokeStyle(lineWidth: 1, dash: [2, 8])
                    )
                    .frame(width: side * 0.58, height: side * 0.58)
                    .rotationEffect(.degrees(reduceMotion ? 0 : 16))

                ForEach(ThreatDirection.allCases) { direction in
                    directionButton(direction)
                        .position(
                            x: center.x + CGFloat(cos(direction.angleRadians)) * radius,
                            y: center.y + CGFloat(sin(direction.angleRadians)) * radius
                        )
                }

                crownCore
                    .position(center)
            }
        }
        .frame(height: 310)
        .padding(.horizontal, 8)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Eight-direction Serpentine Sense compass")
    }

    private func directionButton(_ direction: ThreatDirection) -> some View {
        let isSelected = engine.selectedDirection == direction
        let isThreat = engine.isThreatActive && engine.activeThreat?.direction == direction

        return Button {
            engine.choose(direction: direction)
        } label: {
            ZStack {
                Circle()
                    .fill(
                        isSelected
                            ? aetherGold.opacity(0.95)
                            : isThreat
                                ? aetherViolet.opacity(0.72)
                                : Color.black.opacity(0.46)
                    )
                Circle()
                    .stroke(
                        isThreat ? aetherGold.opacity(0.8) : .white.opacity(0.12),
                        lineWidth: isThreat ? 2 : 1
                    )
                Text(direction.shortLabel)
                    .font(.caption2.monospaced().bold())
                    .foregroundStyle(isSelected ? Color.black : Color.white)
            }
            .frame(width: 48, height: 48)
            .shadow(color: isThreat ? aetherViolet.opacity(0.8) : .clear, radius: 12)
        }
        .buttonStyle(.plain)
        .disabled(!engine.isThreatActive)
        .accessibilityLabel("\(direction.spokenLabel) direction")
        .accessibilityHint(isThreat ? "Serpentine cue detected here" : "Select threat source")
    }

    private var crownCore: some View {
        ZStack {
            Circle()
                .fill(
                    RadialGradient(
                        colors: [
                            (engine.phase == .crownFlare ? aetherGold : aetherViolet).opacity(0.45),
                            Color.black.opacity(0.82)
                        ],
                        center: .center,
                        startRadius: 2,
                        endRadius: 74
                    )
                )
            Circle()
                .stroke(aetherGold.opacity(0.5), lineWidth: 1)
                .padding(7)
            VStack(spacing: 1) {
                Text(engine.phase == .crownFlare ? "CROWN FLARE" : "AETHERCOIL")
                    .font(.caption2.monospaced().bold())
                    .foregroundStyle(aetherGold)
                if engine.activeThreat != nil {
                    Text(String(format: "%.2f", engine.timeRemaining))
                        .font(.title2.monospacedDigit().bold())
                        .foregroundStyle(.white)
                    Text("WORLD SEC")
                        .font(.system(size: 8, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.5))
                } else {
                    Text("◉")
                        .font(.title.bold())
                        .foregroundStyle(.white)
                }
            }
        }
        .frame(width: 126, height: 126)
        .shadow(color: aetherViolet.opacity(0.5), radius: 24)
    }

    private var responseGrid: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Text("CHANNEL RESPONSE")
                    .font(.caption.monospaced().bold())
                    .foregroundStyle(.white.opacity(0.58))
                Spacer()
                if engine.isThreatActive && !engine.canSelectResponse {
                    Text("LOCK DIRECTION FIRST")
                        .font(.caption2.monospaced().bold())
                        .foregroundStyle(aetherGold.opacity(0.82))
                }
            }

            LazyVGrid(columns: responseColumns, spacing: 10) {
                ForEach(SerpentineResponse.allCases) { response in
                    Button {
                        engine.choose(response: response)
                    } label: {
                        HStack(spacing: 9) {
                            Text(response.glyph)
                                .font(.title3.bold())
                                .frame(width: 24)
                            VStack(alignment: .leading, spacing: 1) {
                                Text(response.title.uppercased())
                                    .font(.caption.monospaced().bold())
                                Text(response.instruction)
                                    .font(.system(size: 9, weight: .medium))
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.75)
                                    .opacity(0.6)
                            }
                            Spacer(minLength: 0)
                        }
                        .foregroundStyle(
                            engine.selectedResponse == response ? Color.black : Color.white
                        )
                        .padding(.horizontal, 11)
                        .frame(maxWidth: .infinity, minHeight: 54)
                        .background(
                            engine.selectedResponse == response
                                ? aetherGold
                                : Color.white.opacity(0.07)
                        )
                        .overlay {
                            RoundedRectangle(cornerRadius: 13, style: .continuous)
                                .stroke(.white.opacity(0.10), lineWidth: 1)
                        }
                        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
                    }
                    .buttonStyle(.plain)
                    .disabled(!engine.canSelectResponse)
                    .opacity(engine.canSelectResponse ? 1 : 0.45)
                }
            }
        }
    }

    private var controls: some View {
        VStack(spacing: 11) {
            HStack(spacing: 10) {
                modalityToggle(
                    title: "Audio",
                    systemImage: soundEnabled ? "speaker.wave.2.fill" : "speaker.slash.fill",
                    isOn: $soundEnabled
                )
                modalityToggle(
                    title: "Haptics",
                    systemImage: hapticsEnabled ? "waveform.path" : "waveform.slash",
                    isOn: $hapticsEnabled
                )
            }

            Button {
                engine.primaryAction()
            } label: {
                Text(engine.primaryActionTitle.uppercased())
                    .font(.headline.monospaced().bold())
                    .tracking(0.8)
                    .foregroundStyle(Color.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 15)
                    .background(aetherGold)
                    .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
            }
            .buttonStyle(.plain)
            .disabled(engine.isThreatActive || engine.phase == .waiting)
            .opacity(engine.isThreatActive || engine.phase == .waiting ? 0.48 : 1)

            if engine.isThreatActive {
                Button("Let the omen pass") {
                    engine.ignoreCurrentThreat()
                }
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.62))
                .accessibilityHint("Ignore this cue and preserve player agency")
            }
        }
    }

    private func modalityToggle(
        title: String,
        systemImage: String,
        isOn: Binding<Bool>
    ) -> some View {
        Button {
            isOn.wrappedValue.toggle()
        } label: {
            Label(title, systemImage: systemImage)
                .font(.caption.weight(.semibold))
                .foregroundStyle(isOn.wrappedValue ? aetherJade : .white.opacity(0.45))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 9)
                .background(Color.white.opacity(0.06))
                .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityValue(isOn.wrappedValue ? "On" : "Off")
    }

    private var panelBackground: some ShapeStyle {
        Color.black.opacity(0.34)
    }

    private var aetherGold: Color {
        Color(red: 0.96, green: 0.73, blue: 0.25)
    }

    private var aetherJade: Color {
        Color(red: 0.20, green: 0.91, blue: 0.69)
    }

    private var aetherViolet: Color {
        Color(red: 0.69, green: 0.31, blue: 1.0)
    }
}

#Preview {
    SerpentineSenseView()
}
