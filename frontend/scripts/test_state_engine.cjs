/**
 * Standalone State Engine Automated Verification Script
 */

const { STATE_VISUAL_PROFILES, QUALITY_CONFIGS } = require("../src/components/core/config/coreConfig");
const { StateTransitionManager } = require("../src/components/core/engine/StateTransitionManager");

const ALL_STATES = [
  "IDLE", "LISTENING", "PROCESSING", "THINKING", "SEARCHING",
  "VISION", "REMEMBERING", "ACTING", "SPEAKING", "ERROR"
];

let passed = 0;
let failed = 0;

function assert(condition, name) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${name}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${name}`);
  }
}

console.log("==================================================");
console.log("   SAKI CORE STATE & BEHAVIOR ENGINE TEST SUITE   ");
console.log("==================================================");

// 1. Profile Completeness
console.log("\n1. Verifying 10 State Profiles Completeness:");
for (const st of ALL_STATES) {
  const p = STATE_VISUAL_PROFILES[st];
  assert(!!p, `State ${st} profile defined`);
  assert(p.name === st, `State ${st} profile name match`);
  assert(p.transitionDuration >= 200 && p.transitionDuration <= 1000, `State ${st} transition duration in bounds (${p.transitionDuration}ms)`);
  assert(typeof p.particleFlowMode === "string", `State ${st} particleFlowMode is string (${p.particleFlowMode})`);
}

// 2. Specific Behavioral Invariants
console.log("\n2. Verifying Specific Behavioral Invariants:");
assert(STATE_VISUAL_PROFILES.IDLE.particleDensityFactor <= 0.5, "IDLE has serene low particle density (<= 0.5)");
assert(STATE_VISUAL_PROFILES.LISTENING.outerStructureScale > 1.1, "LISTENING expands outer structure (> 1.1)");
assert(STATE_VISUAL_PROFILES.THINKING.particleDensityFactor === 1.0, "THINKING uses full particle engagement (1.0)");
assert(STATE_VISUAL_PROFILES.SPEAKING.speechHarmonicDepth > 0.5, "SPEAKING enables vocal speech harmonic breathing (> 0.5)");
assert(STATE_VISUAL_PROFILES.SEARCHING.particleFlowMode === "search_radar", "SEARCHING uses search_radar flow mode");
assert(STATE_VISUAL_PROFILES.REMEMBERING.particleFlowMode === "inward_recall", "REMEMBERING uses inward_recall flow mode");
assert(STATE_VISUAL_PROFILES.ACTING.particleFlowMode === "kinetic_vector", "ACTING uses kinetic_vector flow mode");
assert(STATE_VISUAL_PROFILES.VISION.particleFlowMode === "optical_scan", "VISION uses optical_scan flow mode");
assert(STATE_VISUAL_PROFILES.ERROR.particleFlowMode === "restrained_caution", "ERROR uses restrained_caution mode");

// 3. Transition Interpolator
console.log("\n3. Testing Transition Interpolation & Cubic Easing:");
const mgr = new StateTransitionManager("IDLE");
assert(mgr.getCurrentProfile().name === "IDLE", "Initial state is IDLE");

mgr.setState("THINKING");
assert(mgr.getIsTransitioning() === true, "Transition flag active after setState");

const now = 1000;
const pHalf = mgr.update(now + 250);
assert(!isNaN(pHalf.coreRadiusMultiplier), "Interpolated coreRadiusMultiplier is non-NaN");
assert(!isNaN(pHalf.primaryColor.r), "Interpolated primaryColor R is non-NaN");

const pDone = mgr.update(now + 700);
assert(pDone.name === "THINKING", "State arrived at THINKING");
assert(mgr.getIsTransitioning() === false, "Transition marked complete");

// 4. Rapid Mid-Flight Interruption Test
console.log("\n4. Testing Rapid Mid-Flight Transitions (THINKING -> SPEAKING -> LISTENING):");
const rapid = new StateTransitionManager("IDLE");
rapid.setState("THINKING");
rapid.update(now + 50);

rapid.setState("SPEAKING");
const int1 = rapid.update(now + 90);
assert(!isNaN(int1.speechHarmonicDepth), "In-flight speechHarmonicDepth is non-NaN");

rapid.setState("LISTENING");
const int2 = rapid.update(now + 120);
assert(!isNaN(int2.outerStructureScale), "In-flight outerStructureScale is non-NaN");

const intFinal = rapid.update(now + 900);
assert(intFinal.name === "LISTENING", "Rapid transition chain seamlessly resolves to LISTENING");
assert(rapid.getIsTransitioning() === false, "Rapid transition chain completed without leaks");

console.log("\n==================================================");
console.log(`   TOTAL: ${passed} Passed, ${failed} Failed`);
console.log("==================================================");

if (failed > 0) process.exit(1);
