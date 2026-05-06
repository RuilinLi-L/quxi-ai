import { Brain, FileCheck2, FileMusic, WandSparkles } from "lucide-react";
import type { ProjectStatus } from "@/lib/api";

type StageStatus = ProjectStatus | "empty";

const stages = [
  {
    key: "recognize",
    title: "图片处理与 OMR",
    text: "矫正谱面并生成 MusicXML",
    icon: FileMusic,
    active: ["uploaded", "recognizing"] as StageStatus[],
    done: ["recognized", "analyzing", "analyzed", "reporting", "completed"] as StageStatus[]
  },
  {
    key: "review",
    title: "乐谱校验",
    text: "原图、电子谱与 MIDI 对照",
    icon: FileCheck2,
    active: ["recognized"] as StageStatus[],
    done: ["analyzing", "analyzed", "reporting", "completed"] as StageStatus[]
  },
  {
    key: "analysis",
    title: "乐理分析",
    text: "调性、和声、乐句与曲式线索",
    icon: Brain,
    active: ["analyzing"] as StageStatus[],
    done: ["analyzed", "reporting", "completed"] as StageStatus[]
  },
  {
    key: "report",
    title: "中文报告",
    text: "生成课程作业级分析稿",
    icon: WandSparkles,
    active: ["reporting"] as StageStatus[],
    done: ["completed"] as StageStatus[]
  }
] as const;

export function StageGrid({ status }: { status: StageStatus }) {
  return (
    <div className="stage-grid">
      {stages.map((stage) => {
        const Icon = stage.icon;
        const isActive = status !== "empty" && stage.active.includes(status);
        const isDone = status !== "empty" && stage.done.includes(status);
        return (
          <div className={`stage ${isActive ? "active" : ""} ${isDone ? "done" : ""}`} key={stage.key}>
            <Icon size={22} />
            <strong>{stage.title}</strong>
            <span>{stage.text}</span>
          </div>
        );
      })}
    </div>
  );
}
