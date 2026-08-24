/**
 * Saki Audio Reactor Engine Test Suite (Sprint 10)
 * Standalone verification for Web Audio analysis mathematics, frequency band binning,
 * asymmetric attack/decay smoothing, noise floor gating, sensitivity scaling,
 * graceful fallback, and instant cancellation.
 */

// Math simulation replicating AudioAnalyzer signal processing pipeline
class SimulatedAudioAnalyzer {
  constructor(config = {}) {
    this.config = {
      fftSize: 256,
      smoothingTimeConstant: 0.8,
      attackLerp: 0.35,
      decayLerp: 0.08,
      noiseFloor: 0.02,
      sensitivity: 1.0,
      minDecibels: -90,
      maxDecibels: -10,
      ...config
    };
    this.currentMetrics = {
      rawVolume: 0.0,
      smoothedVolume: 0.0,
      lowBand: 0.0,
      midBand: 0.0,
      highBand: 0.0,
      speechActivity: 0.0,
      isAudioActive: false,
      peakFrequency: 0,
      timestamp: Date.now()
    };
    this.isConnected = false;
  }

  setConnected(connected) {
    this.isConnected = connected;
  }

  processFrame(timeDomainBytes, frequencyBytes, sampleRate = 44100) {
    if (!this.isConnected || !timeDomainBytes || !frequencyBytes) {
      this.decayMetrics();
      return this.currentMetrics;
    }

    // 1. RMS volume calculation
    let sumSquares = 0;
    for (let i = 0; i < timeDomainBytes.length; i++) {
      const norm = (timeDomainBytes[i] - 128) / 128.0;
      sumSquares += norm * norm;
    }
    const rms = Math.sqrt(sumSquares / timeDomainBytes.length);
    const scaledVolume = Math.min(1.0, Math.max(0.0, rms * 2.2 * this.config.sensitivity));
    const rawVolume = scaledVolume > this.config.noiseFloor ? scaledVolume : 0.0;

    // 2. Frequency band energy extraction (Peak + Avg blend)
    const binCount = frequencyBytes.length;
    const hzPerBin = (sampleRate / 2) / binCount;

    let lowMax = 0, lowSum = 0, lowCount = 0;
    let midMax = 0, midSum = 0, midCount = 0;
    let highMax = 0, highSum = 0, highCount = 0;
    let maxVal = 0, peakBin = 0;

    for (let i = 0; i < binCount; i++) {
      const freq = i * hzPerBin;
      const val = frequencyBytes[i] / 255.0;

      if (val > maxVal) {
        maxVal = val;
        peakBin = i;
      }

      if (freq >= 20 && freq < 250) {
        lowSum += val;
        if (val > lowMax) lowMax = val;
        lowCount++;
      } else if (freq >= 250 && freq < 2000) {
        midSum += val;
        if (val > midMax) midMax = val;
        midCount++;
      } else if (freq >= 2000 && freq <= 8000) {
        highSum += val;
        if (val > highMax) highMax = val;
        highCount++;
      }
    }

    const lowAvg = lowCount > 0 ? lowSum / lowCount : 0.0;
    const midAvg = midCount > 0 ? midSum / midCount : 0.0;
    const highAvg = highCount > 0 ? highSum / highCount : 0.0;

    const targetLow = (lowMax * 0.65 + lowAvg * 0.35) * this.config.sensitivity;
    const targetMid = (midMax * 0.65 + midAvg * 0.35) * this.config.sensitivity;
    const targetHigh = (highMax * 0.65 + highAvg * 0.35) * this.config.sensitivity;

    const gatedLow = targetLow > this.config.noiseFloor ? Math.min(1.0, targetLow) : 0.0;
    const gatedMid = targetMid > this.config.noiseFloor ? Math.min(1.0, targetMid) : 0.0;
    const gatedHigh = targetHigh > this.config.noiseFloor ? Math.min(1.0, targetHigh) : 0.0;

    // 3. Asymmetric attack/decay smoothing
    const smoothVol = this.applySmoothing(this.currentMetrics.smoothedVolume, rawVolume);
    const smoothLow = this.applySmoothing(this.currentMetrics.lowBand, gatedLow);
    const smoothMid = this.applySmoothing(this.currentMetrics.midBand, gatedMid);
    const smoothHigh = this.applySmoothing(this.currentMetrics.highBand, gatedHigh);

    // 4. Speech activity
    const speechConfidence = Math.min(
      1.0,
      Math.max(0.0, (smoothMid * 0.55 + smoothVol * 0.35 + smoothHigh * 0.1) * 1.4)
    );
    const isAudioActive = smoothVol > 0.015 || speechConfidence > 0.08;

    this.currentMetrics = {
      rawVolume,
      smoothedVolume: smoothVol,
      lowBand: smoothLow,
      midBand: smoothMid,
      highBand: smoothHigh,
      speechActivity: speechConfidence,
      isAudioActive,
      peakFrequency: Math.round(peakBin * hzPerBin),
      timestamp: Date.now()
    };

    return this.currentMetrics;
  }

  applySmoothing(current, target) {
    const factor = target > current ? this.config.attackLerp : this.config.decayLerp;
    const result = current + (target - current) * factor;
    return Math.abs(result) < 0.001 ? 0.0 : Math.min(1.0, Math.max(0.0, result));
  }

  decayMetrics() {
    const decay = this.config.decayLerp;
    this.currentMetrics = {
      rawVolume: 0.0,
      smoothedVolume: Math.max(0.0, this.currentMetrics.smoothedVolume * (1 - decay)),
      lowBand: Math.max(0.0, this.currentMetrics.lowBand * (1 - decay)),
      midBand: Math.max(0.0, this.currentMetrics.midBand * (1 - decay)),
      highBand: Math.max(0.0, this.currentMetrics.highBand * (1 - decay)),
      speechActivity: Math.max(0.0, this.currentMetrics.speechActivity * (1 - decay)),
      isAudioActive: this.currentMetrics.smoothedVolume > 0.01,
      peakFrequency: this.currentMetrics.smoothedVolume > 0.01 ? this.currentMetrics.peakFrequency : 0,
      timestamp: Date.now()
    };
  }

  reset() {
    this.currentMetrics = {
      rawVolume: 0.0,
      smoothedVolume: 0.0,
      lowBand: 0.0,
      midBand: 0.0,
      highBand: 0.0,
      speechActivity: 0.0,
      isAudioActive: false,
      peakFrequency: 0,
      timestamp: Date.now()
    };
  }
}

// Helper to synthesize waveform bytes
function generateSyntheticSineBytes(frequency, sampleRate, durationSamples, amplitude) {
  const timeBytes = new Uint8Array(durationSamples);
  for (let i = 0; i < durationSamples; i++) {
    const t = i / sampleRate;
    const sample = Math.sin(2 * Math.PI * frequency * t) * amplitude;
    timeBytes[i] = Math.round(128 + sample * 127);
  }
  return timeBytes;
}

function generateSyntheticSpectrumBytes(binCount, peakBin, magnitude = 200) {
  const freqBytes = new Uint8Array(binCount);
  for (let i = 0; i < binCount; i++) {
    const dist = Math.abs(i - peakBin);
    const val = Math.max(0, magnitude - dist * 25);
    freqBytes[i] = Math.min(255, val);
  }
  return freqBytes;
}

// -------------------------------------------------------------
// EXECUTE TEST SUITE
// -------------------------------------------------------------
let passed = 0;
let failed = 0;

function assert(condition, description) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${description}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${description}`);
  }
}

console.log("==================================================");
console.log("    SAKI SPRINT 10: AUDIO REACTOR TEST SUITE      ");
console.log("==================================================");

// TEST 1: Initialization & Default Baseline Zero Metrics
console.log("\n1. Testing Initialization & Baseline Default Metrics:");
const analyzer = new SimulatedAudioAnalyzer();
assert(analyzer.currentMetrics.rawVolume === 0, "Initial rawVolume is 0");
assert(analyzer.currentMetrics.smoothedVolume === 0, "Initial smoothedVolume is 0");
assert(analyzer.currentMetrics.isAudioActive === false, "Initial isAudioActive is false");
assert(analyzer.currentMetrics.speechActivity === 0, "Initial speechActivity is 0");

// TEST 2: Mid-Band Vocal Formant Detection (e.g. 500Hz Vowel sound)
console.log("\n2. Testing Vocal Formant Detection (500Hz Tone):");
analyzer.setConnected(true);
const sampleRate = 44100;
const binCount = 128; // 256 FFT -> 128 bins
const hzPerBin = (sampleRate / 2) / binCount; // ~172.26 Hz per bin
const vocalBin = Math.round(500 / hzPerBin); // Bin 3

const vocalTimeBytes = generateSyntheticSineBytes(500, sampleRate, 256, 0.7);
const vocalFreqBytes = generateSyntheticSpectrumBytes(binCount, vocalBin, 220);

// Run 5 iterations to allow attack smoothing to ramp up
let metrics;
for (let i = 0; i < 5; i++) {
  metrics = analyzer.processFrame(vocalTimeBytes, vocalFreqBytes, sampleRate);
}

assert(metrics.rawVolume > 0.3, `Raw volume computed from waveform (${metrics.rawVolume.toFixed(2)})`);
assert(metrics.smoothedVolume > 0.2, `Smoothed volume scaled (${metrics.smoothedVolume.toFixed(2)})`);
assert(metrics.midBand > metrics.lowBand, `Mid-band formant energy (${metrics.midBand.toFixed(2)}) > Low-band (${metrics.lowBand.toFixed(2)})`);
assert(metrics.isAudioActive === true, "isAudioActive is true for vocal speech");
assert(metrics.speechActivity > 0.2, `Speech confidence high (${metrics.speechActivity.toFixed(2)})`);

// TEST 3: Bass / Low-Band Resonance (e.g. 100Hz Deep Voice Pitch)
console.log("\n3. Testing Bass Pitch Resonance (100Hz Tone):");
const bassBin = Math.round(100 / hzPerBin); // Bin 1
const bassTimeBytes = generateSyntheticSineBytes(100, sampleRate, 256, 0.8);
const bassFreqBytes = generateSyntheticSpectrumBytes(binCount, bassBin, 240);

for (let i = 0; i < 5; i++) {
  metrics = analyzer.processFrame(bassTimeBytes, bassFreqBytes, sampleRate);
}
assert(metrics.lowBand > 0.3, `Low-band bass resonance detected (${metrics.lowBand.toFixed(2)})`);

// TEST 4: High-Band Sibilance / Consonant Detection (e.g. 4000Hz 'S' / Fricative)
console.log("\n4. Testing Treble Sibilance / Fricative Detection (4000Hz Tone):");
const trebleBin = Math.round(4000 / hzPerBin); // Bin ~23
const trebleTimeBytes = generateSyntheticSineBytes(4000, sampleRate, 256, 0.6);
const trebleFreqBytes = generateSyntheticSpectrumBytes(binCount, trebleBin, 210);

for (let i = 0; i < 5; i++) {
  metrics = analyzer.processFrame(trebleTimeBytes, trebleFreqBytes, sampleRate);
}
assert(metrics.highBand > 0.3, `High-band sibilance energy detected (${metrics.highBand.toFixed(2)})`);

// TEST 5: Noise Floor Gating (< 0.02 Amplitude Ignored)
console.log("\n5. Testing Noise Floor Gating:");
const silentAnalyzer = new SimulatedAudioAnalyzer({ noiseFloor: 0.05 });
silentAnalyzer.setConnected(true);
const noiseTimeBytes = generateSyntheticSineBytes(500, sampleRate, 256, 0.01); // Whisper-level noise
const noiseFreqBytes = new Uint8Array(binCount); // 0 frequency data

metrics = silentAnalyzer.processFrame(noiseTimeBytes, noiseFreqBytes, sampleRate);
assert(metrics.rawVolume === 0, `Sub-threshold noise gated to 0 (${metrics.rawVolume})`);
assert(metrics.isAudioActive === false, "Low-level background noise does not trigger active speech");

// TEST 6: Asymmetric Attack & Decay Smoothing
console.log("\n6. Testing Asymmetric Attack (Snappy) vs Decay (Gradual):");
const dynamicAnalyzer = new SimulatedAudioAnalyzer({ attackLerp: 0.40, decayLerp: 0.08 });
dynamicAnalyzer.setConnected(true);

// Step 1: Speech onset (0 -> 1.0)
const fullTime = generateSyntheticSineBytes(500, sampleRate, 256, 1.0);
const fullFreq = generateSyntheticSpectrumBytes(binCount, vocalBin, 255);
const onsetMetrics = dynamicAnalyzer.processFrame(fullTime, fullFreq, sampleRate);
assert(onsetMetrics.smoothedVolume >= 0.35, `Fast attack responsiveness on onset (${onsetMetrics.smoothedVolume.toFixed(2)} >= 0.35)`);

// Step 2: Speech release (Silence)
const silenceTime = new Uint8Array(256).fill(128);
const silenceFreq = new Uint8Array(binCount).fill(0);
const release1 = dynamicAnalyzer.processFrame(silenceTime, silenceFreq, sampleRate);
assert(release1.smoothedVolume > 0.25, `Decay is smooth and gradual (${release1.smoothedVolume.toFixed(2)} > 0.25)`);

// Decay for 10 frames
let settledMetrics = release1;
for (let f = 0; f < 15; f++) {
  settledMetrics = dynamicAnalyzer.processFrame(silenceTime, silenceFreq, sampleRate);
}
assert(settledMetrics.smoothedVolume < 0.15, `Metrics gradually settle to quiet level (${settledMetrics.smoothedVolume.toFixed(2)})`);

// TEST 7: Instant Cancellation & Reset (Barge-In / Stop)
console.log("\n7. Testing Immediate Barge-In Cancellation & Metrics Flush:");
dynamicAnalyzer.reset();
assert(dynamicAnalyzer.currentMetrics.smoothedVolume === 0, "Smoothed volume flushed to 0.0");
assert(dynamicAnalyzer.currentMetrics.isAudioActive === false, "isAudioActive flushed to false");
assert(dynamicAnalyzer.currentMetrics.lowBand === 0, "Low band flushed to 0.0");
assert(dynamicAnalyzer.currentMetrics.midBand === 0, "Mid band flushed to 0.0");

// TEST 8: Dynamic Amplitude Sensitivity Tuning
console.log("\n8. Testing Audio Sensitivity Configuration:");
const quietAnalyzer = new SimulatedAudioAnalyzer({ sensitivity: 2.0 });
quietAnalyzer.setConnected(true);
const softTime = generateSyntheticSineBytes(500, sampleRate, 256, 0.2);
const softFreq = generateSyntheticSpectrumBytes(binCount, vocalBin, 80);

const softMetrics = quietAnalyzer.processFrame(softTime, softFreq, sampleRate);
assert(softMetrics.rawVolume > 0.15, `2.0x sensitivity boosts soft speech (${softMetrics.rawVolume.toFixed(2)})`);

// TEST 9: Graceful Fallback When Audio Is Disconnected
console.log("\n9. Testing Graceful Fallback When Disconnected:");
quietAnalyzer.setConnected(false);
const disconnectedMetrics = quietAnalyzer.processFrame(fullTime, fullFreq, sampleRate);
assert(disconnectedMetrics.rawVolume === 0, "Disconnected analyzer yields 0 rawVolume");

// TEST 10: Mathematical Bounds & Non-NaN Invariants
console.log("\n10. Testing Non-NaN & [0.0, 1.0] Range Invariants:");
assert(!isNaN(metrics.rawVolume) && metrics.rawVolume >= 0 && metrics.rawVolume <= 1.0, "rawVolume in [0, 1]");
assert(!isNaN(metrics.smoothedVolume) && metrics.smoothedVolume >= 0 && metrics.smoothedVolume <= 1.0, "smoothedVolume in [0, 1]");
assert(!isNaN(metrics.lowBand) && metrics.lowBand >= 0 && metrics.lowBand <= 1.0, "lowBand in [0, 1]");
assert(!isNaN(metrics.midBand) && metrics.midBand >= 0 && metrics.midBand <= 1.0, "midBand in [0, 1]");
assert(!isNaN(metrics.highBand) && metrics.highBand >= 0 && metrics.highBand <= 1.0, "highBand in [0, 1]");
assert(!isNaN(metrics.speechActivity) && metrics.speechActivity >= 0 && metrics.speechActivity <= 1.0, "speechActivity in [0, 1]");

console.log("\n==================================================");
console.log(`   TOTAL: ${passed} Passed, ${failed} Failed`);
console.log("==================================================");

if (failed > 0) {
  process.exit(1);
}
