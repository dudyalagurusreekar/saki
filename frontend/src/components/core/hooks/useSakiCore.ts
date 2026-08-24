/**
 * useSakiCore React Hook
 * Connects React lifecycle and state events to the CoreRenderer Canvas engine,
 * managing ResizeObserver, Visibility API, and clean teardown.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { SakiState } from "../../../lib/api";
import { QualityLevel } from "../types";
import { CoreRenderer, RendererOptions } from "../engine/CoreRenderer";
import { AudioAnalyzer } from "../engine/AudioAnalyzer";

interface UseSakiCoreProps {
  state?: SakiState;
  activity?: string;
  theme?: "clear_sky" | "night_sky";
  quality?: QualityLevel;
  glowIntensity?: number;
  opacity?: number;
  scale?: number;
  reducedMotion?: boolean;
  showHudTelemetry?: boolean;
  audioSensitivity?: number;
  audioAnalyzer?: AudioAnalyzer;
  onFpsUpdate?: (fps: number) => void;
}

export function useSakiCore(props: UseSakiCoreProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rendererRef = useRef<CoreRenderer | null>(null);
  const [fps, setFps] = useState<number>(60);

  const {
    state = "IDLE",
    activity,
    theme = "night_sky",
    quality = "auto",
    glowIntensity = 1.0,
    opacity = 1.0,
    scale = 1.0,
    reducedMotion = false,
    showHudTelemetry = true,
    audioSensitivity = 1.0,
    audioAnalyzer,
    onFpsUpdate,
  } = props;

  // Initialize renderer on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rendererOptions: RendererOptions = {
      quality,
      glowIntensity,
      reducedMotion,
      theme,
      scale,
      opacity,
      showHudTelemetry,
      audioSensitivity,
      audioAnalyzer,
      onFpsUpdate: (newFps) => {
        setFps(newFps);
        onFpsUpdate?.(newFps);
      },
    };

    const renderer = new CoreRenderer(canvas, rendererOptions);
    rendererRef.current = renderer;
    renderer.setState(state, activity);
    renderer.start();

    // ResizeObserver for container size changes
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          renderer.resize(width, height);
        }
      }
    });

    if (canvas.parentElement) {
      resizeObserver.observe(canvas.parentElement);
    } else {
      resizeObserver.observe(canvas);
    }

    // Page Visibility API to pause rendering when backgrounded
    const handleVisibilityChange = () => {
      if (document.hidden) {
        renderer.stop();
      } else {
        renderer.start();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      resizeObserver.disconnect();
      renderer.destroy();
      rendererRef.current = null;
    };
    // Initializer runs strictly on mount; subsequent options synced in effects below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync state & activity updates
  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.setState(state, activity);
    }
  }, [state, activity]);

  // Sync configuration and theme options
  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.updateOptions({
        quality,
        glowIntensity,
        reducedMotion,
        theme,
        scale,
        opacity,
        showHudTelemetry,
        audioSensitivity,
        audioAnalyzer,
      });
    }
  }, [quality, glowIntensity, reducedMotion, theme, scale, opacity, showHudTelemetry, audioSensitivity, audioAnalyzer]);

  const getRenderer = useCallback(() => rendererRef.current, []);

  return {
    canvasRef,
    fps,
    getRenderer,
  };
}

