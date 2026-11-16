# Implementation Plan: NOOP Home Lab "Liquid Metal" UI Evolution

## 1. Executive Summary
Transform the current functional web dashboard into an exquisite, production-grade interface that captures NOOP's signature **Liquid Metal** design language—characterized by dynamic time-of-day ambient lighting, frosted glass specular highlights, fluid animated gauges, smooth Bézier sparklines, and a native-feeling mobile experience (bottom navigation, safe-area ergonomics, full PWA standalone mode).

---

## 2. Architecture & Design Direction

### 2.1 The "Liquid Metal" & Apple HIG Principles
- **Atmospheric Time-of-Day Ambient Sky**:
  Subtle background radial/linear gradients that shift smoothly based on local hour:
  - Dawn (05:00 - 08:00): Warm rose/amber horizon haze
  - Day (08:00 - 18:00): Crisp azure/cyan atmospheric depth
  - Dusk (18:00 - 21:00): Violet/indigo twilight glow
  - Night (21:00 - 05:00): Deep obsidian with subtle cyan/emerald nebula accents
- **Glassmorphic Depth & Specular Highlights**:
  Replace flat card borders with multi-stop border gradients (`border-t-white/15 border-b-white/5`), inner glows, and layered backdrop blur (`backdrop-blur-xl bg-noop-card/75`).
- **Tabular Monospace Numerics**:
  All live BPMs, recovery percentages, HRV ms, and strain scores use tabular numerical alignment (`font-mono tracking-tight font-variant-numeric: tabular-nums`) so numbers don't jitter during live pulse updates.
- **Mobile First & PWA Standalone**:
  - Full-screen standalone PWA manifest (`display: standalone`, `theme-color: #090a0f`, Apple touch icons).
  - Floating frosted glass bottom tab bar for mobile viewports (`md:hidden`).
  - Safe-area insets (`padding-bottom: env(safe-area-inset-bottom)`).

### 2.2 Component Enhancements
1. **Live Heart Rate Card**:
   - Smooth cubic Bézier spline interpolation for the live sparkline instead of jagged polylines.
   - Glowing trailing head dot that breathes with current BPM.
   - Live pulse indicator with audio-visual rhythm animation.
2. **Recovery Gauge**:
   - Concentric liquid metal progress ring with conic gradient and drop shadow.
   - Metric pills for HRV, RHR, and Sleep with delta comparisons.
3. **Day Strain Meter**:
   - Categorized strain zones: Rest (0–6), Recovery (6–10), Work (10–14), Building (14–18), All-Out (18–21).
   - Dynamic fill that shifts from blue -> green -> amber -> flame red as strain accumulates.
4. **Heart Rate Timeline Chart**:
   - Interactive mouse/touch scrubber with precise time/BPM hover pill.
   - Min / Average / Max reference guidelines.
5. **Auto-Polling & Life-Cycle Management**:
   - Automatic 20-second background polling when page is active.
   - Instant WebSocket reconnect with exponential fallback.

---

## 3. Work Breakdown Structure (Vertical Slices)

```
Phase 1: Design System & Atmospheric Foundations (Tailwind, Glass, Ambient Sky)
    │
Phase 2: Live Biometric Polish (Liquid Recovery, Strain Zones, Bézier Pulse)
    │
Phase 3: Interactive Timeline & Tooltip Scrubber
    │
Phase 4: Mobile Ergonomics & PWA Standalone Manifest
    │
Phase 5: Auto-Sync Lifecycle, Error Boundaries & Build Verification
```

---

## 4. Tasks Specification

### Phase 1: Design System & Ambient Atmospheric Sky
- **Task 1.1**: Extend Tailwind theme with Liquid Metal palettes, specular gradient utilities, and keyframe animations (`shimmer`, `glow`, `skyFade`).
- **Task 1.2**: Create `AmbientSky.tsx` component that computes time-of-day gradients and renders ambient background illumination.
- **Task 1.3**: Update card container styles with layered frosted glass (`backdrop-blur-xl`, `border-t-white/10`, subtle inner shadow).

### Phase 2: Live Biometric Triad Polish
- **Task 2.1**: Rewrite `LiveHeartRate.tsx` with smooth Bézier spline rendering, animated pulse dot, and tabular monospace BPM display.
- **Task 2.2**: Upgrade `RecoveryGauge.tsx` with concentric metallic glow rings, fluid SVG gradient fills, and sub-metric badges.
- **Task 2.3**: Upgrade `StrainMeter.tsx` with segmented zone breakdown (Rest, Active, Building, Extreme) and progress gradient.

### Phase 3: Interactive Timeline & Hardware Telemetry
- **Task 3.1**: Enhance `HeartRateChart.tsx` with an interactive touch/mouse hover scrubber showing exact time and BPM.
- **Task 3.2**: Polish `CollectorStatus.tsx` with gateway latency indicator, battery health badge, and connection telemetry details.

### Phase 4: Mobile Ergonomics & PWA App Experience
- **Task 4.1**: Create `MobileBottomNav.tsx` with frosted glass tab bar, active glow indicators, and safe-area padding.
- **Task 4.2**: Add `manifest.json`, Web App meta tags (`apple-mobile-web-app-capable`, `theme-color`), and SVG icons for home screen installation.

### Phase 5: Auto-Sync Lifecycle & Production Build
- **Task 5.1**: Implement tab-visibility aware 20s polling in `App.tsx` so data stays fresh without manual clicks.
- **Task 5.2**: Build frontend bundle (`npm run build`), verify bundle assets, and test in Docker container.
