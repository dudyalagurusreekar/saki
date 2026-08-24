/**
 * Saki Core State & Behavior Engine Unit Tests (Sprint 3)
 * Tests state visual profiles, rapid interruptible transitions,
 * interpolation bounds, and stability.
 */

import { STATE_VISUAL_PROFILES, QUALITY_CONFIGS } from "../config/coreConfig";
import { StateTransitionManager } from "../engine/StateTransitionManager";
import type { SakiState } from "../../../lib/api";

const ALL_STATES: SakiState[] = [
  "IDLE",
  "LISTENING",
  "PROCESSING",
  "THINKING",
  "SEARCHING",
  "VISION",
  "REMEMBERING",
  "ACTING",
  "SPEAKING",
  "ERROR",
];

export function runStateEngineTests(): { passed: number; failed: number; errors: string[] } {
  let passed = 0;
  let failed = 0;
  const errors: string[] = [];

  function assert(condition: boolean, testName: string) {
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

  // 1. Profile Completeness & Validity
  console.log("\n1. Testing 10 State Visual Profiles Completeness & Boundaries:");
  for (const state of ALL_STATES) {
    const profile = STATE_VISUAL_PROFILES[state];
    assert(!!profile, `Profile exists for ${state}`);
    assert(profile.name === state, `Profile name matches ${state}`);
    assert(profile.coreRadiusMultiplier >= 0.8 && profile.coreRadiusMultiplier <= 2.0, `${state} coreRadiusMultiplier in bounds`);
    assert(profile.corePulsingSpeed >= 0.5 && profile.corePulsingSpeed <= 5.0, `${state} corePulsingSpeed in bounds`);
    assert(profile.transitionDuration >= 200 && profile.transitionDuration <= 1000, `${state} transitionDuration in bounds`);
    assert(typeof profile.particleFlowMode === "string" && profile.particleFlowMode.length > 0, `${state} has valid particleFlowMode (${profile.particleFlowMode})`);
    assert(profile.outerStructureScale >= 0.8 && profile.outerStructureScale <= 2.0, `${state} outerStructureScale in bounds`);
    assert(profile.particleDensityFactor >= 0.3 && profile.particleDensityFactor <= 1.0, `${state} particleDensityFactor in bounds`);
    assert(profile.primaryColor.r >= 0 && profile.primaryColor.r <= 255, `${state} primaryColor R in bounds`);
    assert(profile.primaryColor.g >= 0 && profile.primaryColor.g <= 255, `${state} primaryColor G in bounds`);
    assert(profile.primaryColor.b >= 0 && profile.primaryColor.b <= 255, `${state} primaryColor B in bounds`);
  }

  // 2. Specific Behavioral Invariants
  console.log("\n2. Testing Specific State Behavior Invariants:");
  assert(STATE_VISUAL_PROFILES.IDLE.particleDensityFactor <= 0.5, "IDLE has serene low particle density (<= 0.5)");
  assert(STATE_VISUAL_PROFILES.LISTENING.outerStructureScale > 1.1, "LISTENING expands outer structure (> 1.1)");
  assert(STATE_VISUAL_PROFILES.THINKING.particleDensityFactor === 1.0, "THINKING uses full particle engagement (1.0)");
  assert(STATE_VISUAL_PROFILES.THINKING.constellationLines === true, "THINKING enables neural constellation lines");
  assert(STATE_VISUAL_PROFILES.SPEAKING.speechHarmonicDepth > 0.5, "SPEAKING enables vocal speech harmonic breathing (> 0.5)");
  assert(STATE_VISUAL_PROFILES.SEARCHING.particleFlowMode === "search_radar", "SEARCHING uses search_radar flow mode");
  assert(STATE_VISUAL_PROFILES.REMEMBERING.particleFlowMode === "inward_recall", "REMEMBERING uses inward_recall flow mode");
  assert(STATE_VISUAL_PROFILES.ACTING.particleFlowMode === "kinetic_vector", "ACTING uses kinetic_vector flow mode");
  assert(STATE_VISUAL_PROFILES.VISION.particleFlowMode === "optical_scan", "VISION uses optical_scan flow mode");
  assert(STATE_VISUAL_PROFILES.ERROR.particleFlowMode === "restrained_caution", "ERROR uses restrained_caution mode");

  // 3. State Transition Manager Interpolation Continuity
  console.log("\n3. Testing State Transition Interpolator & Cubic Easing:");
  const manager = new StateTransitionManager("IDLE");
  const initial = manager.getCurrentProfile();
  assert(initial.name === "IDLE", "Initial state is IDLE");

  // Trigger transition IDLE -> THINKING
  manager.setState("THINKING");
  assert(manager.getIsTransitioning() === true, "Transition active after setState");

  // Step at 0ms
  const startProfile = manager.update(performance.now());
  assert(!isNaN(startProfile.coreRadiusMultiplier), "Start radius is non-NaN");

  // Step at 50% time
  const halfProfile = manager.update(performance.now() + 250);
  assert(halfProfile.coreRadiusMultiplier > STATE_VISUAL_PROFILES.IDLE.coreRadiusMultiplier, "Radius interpolated upward toward THINKING");
  assert(!isNaN(halfProfile.primaryColor.r), "Primary color R is non-NaN");

  // Complete transition
  const endProfile = manager.update(performance.now() + 650);
  assert(endProfile.name === "THINKING", "State arrived at THINKING");
  assert(manager.getIsTransitioning() === false, "Transition finished");

  // 4. Rapid Mid-Flight State Interruptions
  console.log("\n4. Testing Rapid Mid-Flight State Interruptions (No Discontinuities):");
  const rapidManager = new StateTransitionManager("IDLE");
  
  // Transition IDLE -> PROCESSING
  rapidManager.setState("PROCESSING");
  rapidManager.update(performance.now() + 50);

  // Interrupt mid-flight with THINKING (50ms in)
  rapidManager.setState("THINKING");
  const int1 = rapidManager.update(performance.now() + 80);
  assert(!isNaN(int1.coreRadiusMultiplier), "Mid-flight radius is valid number");

  // Interrupt mid-flight with SPEAKING (30ms later)
  rapidManager.setState("SPEAKING");
  const int2 = rapidManager.update(performance.now() + 110);
  assert(!isNaN(int2.primaryColor.r), "Mid-flight color is valid number");

  // Interrupt mid-flight with LISTENING (30ms later)
  rapidManager.setState("LISTENING");
  const int3 = rapidManager.update(performance.now() + 140);
  assert(!isNaN(int3.outerStructureScale), "Mid-flight outerStructureScale is valid");

  // Let finish
  const intFinal = rapidManager.update(performance.now() + 800);
  assert(intFinal.name === "LISTENING", "Rapid transition sequence successfully resolves to LISTENING");
  assert(rapidManager.getIsTransitioning() === false, "Rapid transition sequence clean completion");

  // 5. Quality Configurations Verification
  console.log("\n5. Testing Quality Config Presets:");
  assert(QUALITY_CONFIGS.ultra.particleCount === 380, "Ultra quality particle count is 380");
  assert(QUALITY_CONFIGS.high.particleCount === 240, "High quality particle count is 240");
  assert(QUALITY_CONFIGS.medium.particleCount === 140, "Medium quality particle count is 140");
  assert(QUALITY_CONFIGS.low.particleCount === 70, "Low quality particle count is 70");

  console.log(`\n=== Test Results: ${passed} Passed, ${failed} Failed ===\n`);
  return { passed, failed, errors };
}

// Auto-run if executed directly
runStateEngineTests();
