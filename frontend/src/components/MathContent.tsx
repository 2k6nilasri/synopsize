"use client";

import React from "react";
import katex from "katex";

interface MathContentProps {
  content: string;
  displayMode?: boolean;
}

function renderMath(source: string, displayMode: boolean): string {
  const latex = source
    .replace(/^\$\$([\s\S]*)\$\$$/, "$1")
    .replace(/^\\\[([\s\S]*)\\\]$/, "$1")
    .replace(/^\\\(([\s\S]*)\\\)$/, "$1")
    .replace(/^\$([\s\S]*)\$$/, "$1")
    .trim();

  return katex.renderToString(latex, {
    displayMode,
    output: "htmlAndMathml",
    throwOnError: false,
  });
}

export function MathEquation({ content }: MathContentProps) {
  return (
    <div
      className="overflow-x-auto py-2 text-center text-slate-900"
      dangerouslySetInnerHTML={{ __html: renderMath(content, true) }}
    />
  );
}

export default function MathContent({ content }: MathContentProps) {
  const segments = content.split(
    /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|\$[^$\n]+\$)/g
  );

  return (
    <>
      {segments.map((segment, index) => {
        const isMath =
          segment.startsWith("$$") ||
          segment.startsWith("\\[") ||
          segment.startsWith("\\(") ||
          segment.startsWith("$");

        if (!isMath) return <React.Fragment key={index}>{segment}</React.Fragment>;

        const displayMode =
          segment.startsWith("$$") || segment.startsWith("\\[");
        return (
          <span
            key={index}
            className={displayMode ? "block overflow-x-auto py-1" : "inline-block"}
            dangerouslySetInnerHTML={{
              __html: renderMath(segment, displayMode),
            }}
          />
        );
      })}
    </>
  );
}
