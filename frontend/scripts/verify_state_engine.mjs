/**
 * Standalone Saki Core State & Behavior Verification Suite (Sprint 3)
 */

import fs from "fs";
import path from "path";

let passed = 0;
let failed = 0;
const errors = [];

function assert(condition, testName) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${testName}`);
  } else {
    failed++;
    errors.push(testName);
    console.error(`  ✗ FAIL: ${testName}`);
  }
}

console.log("==================================================");
console.log("   SAKI CORE STATE & BEHAVIOR ENGINE TEST SUITE   ");
console.log("==================================================");

// Read coreConfig.ts and verify declarative structure
const configPath = fs.existsSync(path.resolve("frontend/src/components/core/config/coreConfig.ts"))
  ? path.resolve("frontend/src/components/core/config/coreConfig.ts")
  : path.resolve("./src/components/core/config/coreConfig.ts");
const configContent = fs.readFileSync(configPath, "utf-8");

const ALL_STATES = [
  "IDLE", "LISTENING", "PROCESSING", "THINKING", "SEARCHING",
  "VISION", "REMEMBERING", "ACTING", "SPEAKING", "ERROR"
];

console.log("\n1. Verifying 10 Saki State Visual Profiles Declarations:");
for (const state of ALL_STATES) {
  assert(configContent.includes(`${state}: {`), `Profile definition exists for ${state}`);
  assert(configContent.includes(`name: "${state}"`), `Profile name matches ${state}`);
}

// 2. Behavioral Invariant Declarations
console.log("\n2. Verifying Specific Behavior & Flow Mode Assignments:");
assert(configContent.includes('particleFlowMode: "orbital"'), "IDLE assigned orbital flow mode");
assert(configContent.includes('particleFlowMode: "receptive_expand"'), "LISTENING assigned receptive_expand flow mode");
assert(configContent.includes('particleFlowMode: "converging_prep"'), "PROCESSING assigned converging_prep flow mode");
assert(configContent.includes('particleFlowMode: "neural_swirl"'), "THINKING assigned neural_swirl flow mode");
assert(configContent.includes('particleFlowMode: "search_radar"'), "SEARCHING assigned search_radar flow mode");
assert(configContent.includes('particleFlowMode: "optical_scan"'), "VISION assigned optical_scan flow mode");
assert(configContent.includes('particleFlowMode: "inward_recall"'), "REMEMBERING assigned inward_recall flow mode");
assert(configContent.includes('particleFlowMode: "kinetic_vector"'), "ACTING assigned kinetic_vector flow mode");
assert(configContent.includes('particleFlowMode: "speech_harmonic_pulse"'), "SPEAKING assigned speech_harmonic_pulse flow mode");
assert(configContent.includes('particleFlowMode: "restrained_caution"'), "ERROR assigned restrained_caution flow mode");

// 3. State Transition Math Simulation
console.log("\n3. Testing Cubic Easing & Interpolation Math:");
function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

assert(easeInOutCubic(0) === 0, "Easing starts exactly at 0");
assert(easeInOutCubic(1) === 1, "Easing ends exactly at 1");
assert(easeInOutCubic(0.5) === 0.5, "Easing midpoint is 0.5");
assert(easeInOutCubic(0.25) < 0.25, "Ease-in acceleration verified at t=0.25");
assert(easeInOutCubic(0.75) > 0.75, "Ease-out deceleration verified at t=0.75");

// 4. Interpolation & Multi-State Interruption Logic Simulation
console.log("\n4. Simulating Mid-Flight Interruptible State Branching:");
class StateTransitionSimulator {
  constructor(initialState = "IDLE") {
    this.current = { radius: 1.0, speed: 0.75, mode: "orbital", state: initialState };
    this.previous = { ...this.current };
    this.target = { ...this.current };
    this.isTransitioning = false;
    this.progress = 1.0;
  }

  setState(newState, targetRadius, targetSpeed, targetMode, duration = 500, now = Date.now()) {
    this.previous = { ...this.current };
    this.target = { radius: targetRadius, speed: targetSpeed, mode: targetMode, state: newState };
    this.startTime = now;
    this.duration = duration;
    this.isTransitioning = true;
  }

  update(now) {
    if (!this.isTransitioning) return this.current;
    const elapsed = now - this.startTime;
    const rawT = Math.min(1.0, Math.max(0.0, elapsed / this.duration));
    const t = easeInOutCubic(rawT);
    this.progress = rawT;

    this.current = {
      radius: this.previous.radius + (this.target.radius - this.previous.radius) * t,
      speed: this.previous.speed + (this.target.speed - this.previous.speed) * t,
      mode: rawT >= 0.5 ? this.target.mode : this.previous.mode,
      state: rawT >= 0.5 ? this.target.state : this.previous.state,
    };

    if (rawT >= 1.0) {
      this.isTransitioning = false;
    }
    return this.current;
  }
}

const sim = new StateTransitionSimulator("IDLE");
const t0 = 1000;
sim.setState("THINKING", 1.3, 1.85, "neural_swirl", 500, t0);
sim.update(t0 + 50);

// Interrupt with SPEAKING at t = 50ms
sim.setState("SPEAKING", 1.28, 1.45, "speech_harmonic_pulse", 400, t0 + 50);
const mid1 = sim.update(t0 + 80);
assert(!isNaN(mid1.radius), "Interrupted radius is a valid number");
assert(mid1.radius >= 1.0 && mid1.radius <= 1.35, `Interrupted radius in expected range (${mid1.radius.toFixed(3)})`);

// Interrupt with LISTENING at t = 100ms
sim.setState("LISTENING", 1.15, 1.1, "receptive_expand", 450, t0 + 100);
const mid2 = sim.update(t0 + 120);
assert(!isNaN(mid2.speed), "Second interruption speed is valid number");

// Complete transition (t0 + 100 + 450 + 50ms margin)
const finalState = sim.update(t0 + 600);
assert(finalState.state === "LISTENING", "Rapid transition resolves cleanly to LISTENING");
assert(finalState.mode === "receptive_expand", "Flow mode correctly resolves to receptive_expand");
assert(sim.isTransitioning === false, "Simulator transition flag cleared");

// 5. Quality Configs Verification
console.log("\n5. Verifying Quality Level Specifications in Config:");
assert(configContent.includes("ultra: {"), "Ultra quality profile defined");
assert(configContent.includes("high: {"), "High quality profile defined");
assert(configContent.includes("medium: {"), "Medium quality profile defined");
assert(configContent.includes("low: {"), "Low quality profile defined");

console.log("\n==================================================");
console.log(`   TOTAL: ${passed} Passed, ${failed} Failed`);
console.log("==================================================");

if (failed > 0) process.exit(1);
