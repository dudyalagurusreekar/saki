"""
Reliability and Architecture Test Suite: Separate Chat & Core Experiences UI Redesign
Verifies:
1. Two distinct frontend experiences: Chat Workspace and Dedicated Saki Core Page.
2. Exact state color mappings for all 10 Saki states (Listening, Thinking, Speaking, Idle, Searching, Vision, Remembering, Acting, Error).
3. Chat Page does NOT contain the 3D Core canvas behind chat messages.
4. Pure black (#000000) dedicated Saki Core view with minimal HUD.
5. Navigation persistence (shared conversation, memory, language, and voice state).
6. Next.js route structure for both root and /core endpoints.
"""

import os
import re
import pytest

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
CONFIG_FILE = os.path.join(FRONTEND_DIR, "src", "components", "core", "config", "coreConfig.ts")
CHAT_WINDOW_FILE = os.path.join(FRONTEND_DIR, "src", "components", "ChatWindow.tsx")
SAKI_CORE_PAGE_FILE = os.path.join(FRONTEND_DIR, "src", "components", "SakiCorePage.tsx")
TOP_BAR_FILE = os.path.join(FRONTEND_DIR, "src", "components", "TopBar.tsx")
SIDEBAR_FILE = os.path.join(FRONTEND_DIR, "src", "components", "Sidebar.tsx")
GLOBALS_CSS_FILE = os.path.join(FRONTEND_DIR, "src", "app", "globals.css")
CORE_ROUTE_FILE = os.path.join(FRONTEND_DIR, "src", "app", "core", "page.tsx")


class TestSeparateChatAndCoreUI:
    """Test suite validating the separate Chat and Core architecture."""

    def test_01_component_files_exist(self):
        """Verify all required component and route files exist."""
        assert os.path.isfile(CONFIG_FILE), "coreConfig.ts must exist"
        assert os.path.isfile(CHAT_WINDOW_FILE), "ChatWindow.tsx must exist"
        assert os.path.isfile(SAKI_CORE_PAGE_FILE), "SakiCorePage.tsx must exist"
        assert os.path.isfile(TOP_BAR_FILE), "TopBar.tsx must exist"
        assert os.path.isfile(SIDEBAR_FILE), "Sidebar.tsx must exist"
        assert os.path.isfile(GLOBALS_CSS_FILE), "globals.css must exist"
        assert os.path.isfile(CORE_ROUTE_FILE), "app/core/page.tsx must exist"

    def test_02_core_state_colors_exact_match(self):
        """Verify Saki Core visual profile state colors match the exact user specification."""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # 🟢 LISTENING: Green
        listening_match = re.search(r"LISTENING:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*16,\s*g:\s*185,\s*b:\s*129", content)
        assert listening_match, "LISTENING must use Emerald Green primary color {r: 16, g: 185, b: 129}"

        # 🟡 THINKING: Yellow / Gold
        thinking_match = re.search(r"THINKING:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*245,\s*g:\s*190,\s*b:\s*11", content)
        assert thinking_match, "THINKING must use Yellow/Gold primary color {r: 245, g: 190, b: 11}"

        # 🔴 SPEAKING: Warm Red
        speaking_match = re.search(r"SPEAKING:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*239,\s*g:\s*68,\s*b:\s*68", content)
        assert speaking_match, "SPEAKING must use Warm Red primary color {r: 239, g: 68, b: 68}"

        # ⚪ IDLE: Soft White / Neutral Silver
        idle_match = re.search(r"IDLE:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*245,\s*g:\s*248,\s*b:\s*255", content)
        assert idle_match, "IDLE must use Soft White/Silver primary color {r: 245, g: 248, b: 255}"

        # 🔵 SEARCHING: Blue
        searching_match = re.search(r"SEARCHING:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*59,\s*g:\s*130,\s*b:\s*246", content)
        assert searching_match, "SEARCHING must use Electric Blue primary color {r: 59, g: 130, b: 246}"

        # 🟣 VISION: Purple
        vision_match = re.search(r"VISION:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*168,\s*g:\s*85,\s*b:\s*247", content)
        assert vision_match, "VISION must use Vibrant Purple primary color {r: 168, g: 85, b: 247}"

        # 💠 REMEMBERING: Cyan / Teal
        remembering_match = re.search(r"REMEMBERING:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*20,\s*g:\s*184,\s*b:\s*166", content)
        assert remembering_match, "REMEMBERING must use Cyan/Teal primary color {r: 20, g: 184, b: 166}"

        # 🟠 ACTING: Kinetic Orange
        acting_match = re.search(r"ACTING:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*249,\s*g:\s*115,\s*b:\s*22", content)
        assert acting_match, "ACTING must use Kinetic Orange primary color {r: 249, g: 115, b: 22}"

        # ⚠️ ERROR: Controlled Warning Crimson
        error_match = re.search(r"ERROR:\s*\{[^}]*primaryColor:\s*\{\s*r:\s*220,\s*g:\s*38,\s*b:\s*38", content)
        assert error_match, "ERROR must use Crimson Warning primary color {r: 220, g: 38, b: 38}"

    def test_03_saki_core_page_pure_black_and_minimal_hud(self):
        """Verify SakiCorePage has pure black background (#000000) and dedicated HUD."""
        with open(SAKI_CORE_PAGE_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        assert "bg-black" in content or "#000000" in content, "SakiCorePage must have deep pure black background"
        assert "<SakiCore" in content, "SakiCorePage must render full-screen SakiCore canvas"
        assert "onSwitchToChat" in content, "SakiCorePage must provide instant switch to Chat workspace"
        assert "isVoiceActive" in content, "SakiCorePage must support direct hands-free voice toggling"
        assert "detectedLanguage" in content, "SakiCorePage must display active spoken language"

    def test_04_chat_page_does_not_render_core_in_background(self):
        """Verify Chat page renders clean conversation without SakiCore canvas in the background."""
        with open(CHAT_WINDOW_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # In ChatWindow, activeView === 'core' renders SakiCorePage, while activeView === 'chat' renders Chat view without SakiCore
        assert "activeView === \"core\" ? (" in content or "activeView === 'core' ? (" in content, "ChatWindow must conditionally switch between Core and Chat views"
        
        # Verify Chat view branch contains Conversation Stream but not raw SakiCore behind chat
        chat_branch_split = content.split("activeView === \"core\" ?")[1]
        core_branch, chat_branch = chat_branch_split.split(":", 1)

        assert "<SakiCorePage" in core_branch, "Core branch must render SakiCorePage"
        assert "<MessageBubble" in chat_branch, "Chat branch must render MessageBubble conversation"
        assert "<SakiCore" not in chat_branch, "Chat branch must NOT render SakiCore canvas behind chat messages"

    def test_05_navigation_and_state_preservation(self):
        """Verify navigation controls exist in TopBar and Sidebar while state is shared in ChatWindow."""
        with open(TOP_BAR_FILE, "r", encoding="utf-8") as f:
            top_bar = f.read()

        assert "activeView" in top_bar, "TopBar must support activeView"
        assert "onSelectView" in top_bar, "TopBar must provide onSelectView callback"

        with open(SIDEBAR_FILE, "r", encoding="utf-8") as f:
            sidebar = f.read()

        assert "activeView" in sidebar, "Sidebar must support activeView"
        assert "onSelectView" in sidebar, "Sidebar must provide onSelectView callback"

    def test_06_css_themes_support(self):
        """Verify globals.css contains Dark ChatGPT-inspired environment and Clear Sky light theme."""
        with open(GLOBALS_CSS_FILE, "r", encoding="utf-8") as f:
            css = f.read()

        assert 'data-theme="clear_sky"' in css, "Clear sky light theme must be defined in globals.css"
        assert 'data-theme="night_sky"' in css or "--background: #171717" in css, "Dark ChatGPT-inspired theme must be defined"
