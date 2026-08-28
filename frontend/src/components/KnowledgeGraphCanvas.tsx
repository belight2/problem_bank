import { useEffect, useMemo, useRef } from "react";
import cytoscape, {
  type ElementDefinition,
  type StylesheetJson,
} from "cytoscape";

import type { KnowledgeGraph, KnowledgeGraphNode } from "../types";

interface KnowledgeGraphCanvasProps {
  graph: KnowledgeGraph;
}

// 개념 숙련도 색: cividis 계열(파랑→노랑) 순차 램프. 색약 안전하고
// 타입 팔레트(초록/빨강/앰버)와 겹치지 않아 오개념 노드와 혼동되지 않는다.
const MASTERY_RAMP = ["#00204d", "#414d6b", "#7c7b78", "#bcaf6f", "#ffe945"];
const UNATTEMPTED_COLOR = "#f0f4f2";
// graded_count가 이 값 미만이면 라벨에 ~를 붙여 표본이 적음을 표시(백엔드 LOW_SAMPLE_THRESHOLD와 일치).
const LOW_SAMPLE_THRESHOLD = 3;

function masteryColor(score: number | null): string {
  if (score == null) return UNATTEMPTED_COLOR;
  const clamped = Math.min(1, Math.max(0, score));
  const index = Math.min(
    MASTERY_RAMP.length - 1,
    Math.floor(clamped * MASTERY_RAMP.length),
  );
  return MASTERY_RAMP[index];
}

// 색만으로 판단하지 않도록 개념 라벨에 숙련도 %를 함께 노출(색약/모노 대비).
function conceptLabel(node: KnowledgeGraphNode): string {
  if (node.mastery_score == null || node.attempted === false) {
    return `${node.label} · 미평가`;
  }
  const percent = Math.round(node.mastery_score * 100);
  const graded = (node.correct_count ?? 0) + (node.incorrect_count ?? 0);
  const prefix = graded < LOW_SAMPLE_THRESHOLD ? "~" : "";
  return `${node.label} · ${prefix}${percent}%`;
}

const graphStyles: StylesheetJson = [
  {
    selector: "node",
    style: {
      width: 54,
      height: 54,
      label: "data(label)",
      "background-color": "#ffffff",
      "border-color": "#b8c6bd",
      "border-width": 2,
      color: "#17201a",
      "font-family": "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
      "font-size": 11,
      "font-weight": 600,
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 9,
      "text-wrap": "ellipsis",
      "text-max-width": "130px",
      "overlay-opacity": 0,
      "transition-property": "background-color, border-color, border-width, opacity",
      "transition-duration": 100,
    },
  },
  {
    selector: "node.card",
    style: {
      width: 72,
      height: 72,
      "background-color": "#22c55e",
      "border-color": "#16a34a",
      "border-width": 3,
      color: "#0b3d20",
      "font-size": 13,
      "font-weight": 700,
      "text-margin-y": 11,
    },
  },
  {
    selector: "node.topic",
    style: {
      shape: "round-rectangle",
      width: 58,
      height: 46,
      "background-color": "#fffbeb",
      "border-color": "#f59e0b",
    },
  },
  {
    selector: "node.problem",
    style: {
      shape: "round-rectangle",
      "background-color": "#dcfce7",
      "border-color": "#22c55e",
    },
  },
  {
    selector: "node.note",
    style: {
      shape: "round-diamond",
      "background-color": "#ffffff",
      "border-color": "#16a34a",
    },
  },
  {
    selector: "node.concept",
    style: {
      width: 62,
      height: 62,
      // 숙련도 램프 색(개념 노드마다 data.masteryColor로 주입). 테두리는 고정해 '개념'임을 유지.
      "background-color": "data(masteryColor)",
      "border-color": "#16a34a",
      color: "#17201a",
    },
  },
  {
    selector: "node.misconception",
    style: {
      shape: "hexagon",
      "background-color": "#fef2f2",
      "border-color": "#ef4444",
    },
  },
  {
    selector: "node.unknown",
    style: {
      "background-color": "#f0f4f2",
      "border-style": "dashed",
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#17201a",
      "border-width": 4,
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      label: "data(label)",
      "line-color": "#b8c6bd",
      "target-arrow-color": "#849188",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.8,
      "curve-style": "bezier",
      color: "#5f6f65",
      "font-family": "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
      "font-size": 8,
      "font-weight": 500,
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.88,
      "text-background-padding": "3px",
      "text-rotation": "autorotate",
      "text-wrap": "ellipsis",
      "text-max-width": "90px",
      "overlay-opacity": 0,
      "transition-property": "line-color, target-arrow-color, width, opacity",
      "transition-duration": 100,
    },
  },
  {
    selector: "edge:selected",
    style: {
      width: 3,
      "line-color": "#22c55e",
      "target-arrow-color": "#16a34a",
    },
  },
];

export function KnowledgeGraphCanvas({ graph }: KnowledgeGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const elements = useMemo<ElementDefinition[]>(() => [
    ...graph.nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.type === "concept" ? conceptLabel(node) : node.label,
        nodeType: node.type,
        ...(node.type === "concept"
          ? { masteryColor: masteryColor(node.mastery_score) }
          : {}),
      },
      classes: node.type,
    })),
    ...graph.edges.map((edge) => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        relationType: edge.type,
      },
    })),
  ], [graph.edges, graph.nodes]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const instance = cytoscape({
      container,
      elements,
      style: graphStyles,
      layout: {
        name: "cose",
        animate: graph.nodes.length <= 80,
        animationDuration: 320,
        fit: true,
        padding: 48,
        nodeRepulsion: 8200,
        idealEdgeLength: 110,
        edgeElasticity: 90,
        nestingFactor: 1.2,
        gravity: 0.35,
        numIter: 1000,
        randomize: true,
      },
      minZoom: 0.2,
      maxZoom: 2.5,
      boxSelectionEnabled: false,
      selectionType: "single",
      wheelSensitivity: 0.22,
    });

    const resizeObserver = new ResizeObserver(() => {
      instance.resize();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      instance.destroy();
    };
  }, [elements, graph.nodes.length]);

  return (
    <div className="knowledge-graph-canvas-shell">
      <div
        ref={containerRef}
        className="knowledge-graph-canvas"
        role="img"
        aria-label={`${graph.nodes.length}개 노드와 ${graph.edges.length}개 관계로 구성된 지식 그래프`}
        tabIndex={0}
      />
      <div className="knowledge-graph-legend">
        <span className="knowledge-graph-legend-title">개념 숙련도</span>
        <span className="knowledge-graph-legend-scale">
          <span className="knowledge-graph-legend-label">약함</span>
          <span className="knowledge-graph-legend-ramp" />
          <span className="knowledge-graph-legend-label">강함</span>
        </span>
        <span className="knowledge-graph-legend-scale">
          <span className="knowledge-graph-legend-swatch" />
          <span className="knowledge-graph-legend-label">미평가</span>
        </span>
        <span className="knowledge-graph-legend-note">숫자 = 정답률 %</span>
      </div>
    </div>
  );
}
