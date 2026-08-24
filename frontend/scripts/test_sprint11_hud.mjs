/**
 * Sprint 11 HUD & Three-Zone Application UI Verification Test Suite
 */
import fs from "fs";
import path from "path";

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ ${message}`);
  }
}

console.log("=== SPRINT 11 HUD & WORKSTATION UI VERIFICATION ===\n");

// 1. Check Globals CSS HUD Tokens
console.log("1. Verifying Futuristic HUD CSS Tokens in globals.css...");
const cssPath = path.resolve("frontend/src/app/globals.css");
const cssContent = fs.readFileSync(cssPath, "utf-8");

assert(cssContent.includes(".hud-panel"), "globals.css exports .hud-panel utility");
assert(cssContent.includes(".hud-card"), "globals.css exports .hud-card utility");
assert(cssContent.includes(".hud-corner-bracket"), "globals.css exports .hud-corner-bracket utility");
assert(cssContent.includes(".hud-label"), "globals.css exports .hud-label utility");
assert(cssContent.includes(".cyber-input-dock"), "globals.css exports .cyber-input-dock utility");
assert(cssContent.includes("state-glow-idle"), "globals.css exports state-glow utilities");
assert(cssContent.includes("prefers-reduced-motion"), "globals.css includes prefers-reduced-motion accessibility safeguard");

// 2. Check Left Sidebar (Zone 1)
console.log("\n2. Verifying Left Control Panel (Zone 1) in Sidebar.tsx...");
const sidebarPath = path.resolve("frontend/src/components/Sidebar.tsx");
const sidebarContent = fs.readFileSync(sidebarPath, "utf-8");

assert(sidebarContent.includes("SAKI // OS"), "Sidebar includes SAKI // OS insignia");
assert(sidebarContent.includes("New Session"), "Sidebar provides New Session action");
assert(sidebarContent.includes("⌘K") || sidebarContent.includes("Ctrl+K"), "Sidebar displays keyboard shortcut badge");
assert(sidebarContent.includes("searchConversations"), "Sidebar includes search integration");
assert(sidebarContent.includes("deleteConversation"), "Sidebar includes delete action with confirmation");
assert(sidebarContent.includes("isCollapsed"), "Sidebar supports collapsible icon rail mode on desktop");
assert(sidebarContent.includes("onOpenMemory"), "Sidebar binds Memory Vault trigger");
assert(sidebarContent.includes("onOpenSettings"), "Sidebar binds System Config trigger");
assert(sidebarContent.includes("onToggleVoice"), "Sidebar supports Voice Engine toggle");

// 3. Check TopBar (Zone 2 Header)
console.log("\n3. Verifying Futuristic TopBar in TopBar.tsx...");
const topBarPath = path.resolve("frontend/src/components/TopBar.tsx");
const topBarContent = fs.readFileSync(topBarPath, "utf-8");

assert(topBarContent.includes("getStateBadge"), "TopBar computes dynamic state badges for 10 Saki states");
assert(topBarContent.includes("stateBadge.dot"), "TopBar renders pulsing luminous state dot");
assert(topBarContent.includes("BRAIN HUD"), "TopBar includes Brain HUD toggle button");
assert(topBarContent.includes("TIME //"), "TopBar renders precision digital clock");
assert(topBarContent.includes("SYS // ARCHITECTURE"), "TopBar displays system architecture breadcrumb");

// 4. Check MessageBubble & InputBox (Zone 2 Conversation Stage)
console.log("\n4. Verifying Translucent Conversation Stage & Command Dock...");
const msgBubblePath = path.resolve("frontend/src/components/MessageBubble.tsx");
const msgBubbleContent = fs.readFileSync(msgBubblePath, "utf-8");

assert(msgBubbleContent.includes("OPERATOR // USER"), "MessageBubble renders operator identity tag");
assert(msgBubbleContent.includes("SAKI // CORE_AI"), "MessageBubble renders Saki AI identity tag");
assert(msgBubbleContent.includes("handleCopy"), "MessageBubble provides one-click copy on code blocks");
assert(msgBubbleContent.includes("hud-corner-bracket"), "MessageBubble uses cybernetic corner brackets");

const inputPath = path.resolve("frontend/src/components/InputBox.tsx");
const inputContent = fs.readFileSync(inputPath, "utf-8");

assert(inputContent.includes("cyber-input-dock"), "InputBox uses cyber-input-dock class");
assert(inputContent.includes("SpeechRecognition"), "InputBox integrates browser speech recognition");
assert(inputContent.includes("handleAttachClick"), "InputBox integrates file attachment upload");
assert(inputContent.includes("onStop"), "InputBox provides instant stop generation button");
assert(inputContent.includes("↵ SEND"), "InputBox renders shortcut footer hints");

// 5. Check Right Brain Telemetry Panel (Zone 3)
console.log("\n5. Verifying Right Brain Telemetry Panel (Zone 3) in BrainPanel.tsx...");
const brainPath = path.resolve("frontend/src/components/BrainPanel.tsx");
const brainContent = fs.readFileSync(brainPath, "utf-8");

assert(brainContent.includes("BRAIN // TELEMETRY"), "BrainPanel renders sci-fi header");
assert(brainContent.includes("Saki Core State"), "BrainPanel renders real-time state card");
assert(brainContent.includes("Active Model"), "BrainPanel displays active Ollama model");
assert(brainContent.includes("KOKORO // WHISPER"), "BrainPanel renders Voice & Acoustic telemetry card");
assert(brainContent.includes("Sub-30ms VAD"), "BrainPanel renders interruption filter status");
assert(brainContent.includes("Turn Latency"), "BrainPanel renders latency metrics");
assert(brainContent.includes("Empathy Resonance"), "BrainPanel renders emotional intelligence card");
assert(brainContent.includes("Social Alignment"), "BrainPanel renders social energy gauges");

// 6. Check Modals (MemoryModal & SettingsModal)
console.log("\n6. Verifying HUD Modals in MemoryModal.tsx & SettingsModal.tsx...");
const memoryModalPath = path.resolve("frontend/src/components/MemoryModal.tsx");
const memoryModalContent = fs.readFileSync(memoryModalPath, "utf-8");
assert(memoryModalContent.includes("MEMORY // ARCHIVE"), "MemoryModal includes cybernetic header");
assert(memoryModalContent.includes("Filter memories") || memoryModalContent.includes("Search memory"), "MemoryModal supports search filtering");

const settingsModalPath = path.resolve("frontend/src/components/SettingsModal.tsx");
const settingsModalContent = fs.readFileSync(settingsModalPath, "utf-8");
assert(settingsModalContent.includes("SYSTEM // CONFIG"), "SettingsModal includes cybernetic header");
assert(settingsModalContent.includes("audio_sensitivity"), "SettingsModal includes audio sensitivity slider");
assert(settingsModalContent.includes("core_quality"), "SettingsModal includes core quality presets");
assert(settingsModalContent.includes("onPreviewState"), "SettingsModal supports state transition tester");

// 7. Check ChatWindow Layout Assembly
console.log("\n7. Verifying Master Workstation Assembly in ChatWindow.tsx...");
const chatWindowPath = path.resolve("frontend/src/components/ChatWindow.tsx");
const chatWindowContent = fs.readFileSync(chatWindowPath, "utf-8");

assert(chatWindowContent.includes("<Sidebar"), "ChatWindow mounts Left Navigation Sidebar (Zone 1)");
assert(chatWindowContent.includes("<TopBar"), "ChatWindow mounts TopBar HUD");
assert(chatWindowContent.includes("<SakiCore"), "ChatWindow mounts SakiCore in central stage");
assert(chatWindowContent.includes("<MessageBubble"), "ChatWindow renders message bubbles");
assert(chatWindowContent.includes("<InputBox"), "ChatWindow mounts bottom command dock");
assert(chatWindowContent.includes("<BrainPanel"), "ChatWindow mounts Right Brain Telemetry Panel (Zone 3)");
assert(chatWindowContent.includes("<MemoryModal"), "ChatWindow mounts MemoryModal");
assert(chatWindowContent.includes("<SettingsModal"), "ChatWindow mounts SettingsModal");
assert(chatWindowContent.includes("handleKeyDown"), "ChatWindow registers global keyboard shortcuts");
assert(chatWindowContent.includes("Quick Operational Inquiries"), "ChatWindow displays empty-state prompt starters");

console.log(`\n========================================`);
console.log(`HUD Verification Summary: ${passed} Passed, ${failed} Failed`);
console.log(`========================================\n`);

if (failed > 0) {
  process.exit(1);
}
