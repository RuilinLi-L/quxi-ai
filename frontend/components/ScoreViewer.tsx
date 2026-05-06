"use client";

import { useEffect, useRef, useState } from "react";
import { FileMusic } from "lucide-react";
import { apiUrl } from "@/lib/api";

type ScoreViewerProps = {
  musicxmlUrl: string | null | undefined;
};

export function ScoreViewer({ musicxmlUrl }: ScoreViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [message, setMessage] = useState("等待 MusicXML 识别结果");

  useEffect(() => {
    let cancelled = false;

    async function renderScore() {
      if (!musicxmlUrl || !containerRef.current) {
        return;
      }

      setMessage("正在渲染电子乐谱...");
      containerRef.current.innerHTML = "";

      try {
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        const osmd = new OpenSheetMusicDisplay(containerRef.current, {
          autoResize: true,
          drawTitle: true,
          drawSubtitle: false,
          backend: "svg"
        });
        const response = await fetch(apiUrl(musicxmlUrl));
        const xml = await response.text();
        if (cancelled) {
          return;
        }
        await osmd.load(xml);
        osmd.render();
        setMessage("");
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "乐谱渲染失败");
      }
    }

    renderScore();

    return () => {
      cancelled = true;
    };
  }, [musicxmlUrl]);

  return (
    <div className="musicxml-viewer">
      <div ref={containerRef} />
      {message ? (
        <div className="viewer-fallback">
          <FileMusic size={34} />
          <p>{message}</p>
        </div>
      ) : null}
    </div>
  );
}
