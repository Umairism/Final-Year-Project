import React from 'react';

export const SafeMarkdown = ({ text }: { text: string }) => {
  const lines = text.split(/\r?\n/);
  return <div className="space-y-2 whitespace-pre-wrap">{lines.map((line, index) => {
    const heading = line.match(/^#{1,3}\s+(.*)$/);
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const content = heading?.[1] ?? bullet?.[1] ?? numbered?.[1] ?? line;
    const parts = content.split(/(\*\*[^*]+\*\*)/g).map((part, i) => part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <React.Fragment key={i}>{part}</React.Fragment>);
    if (heading) return <h4 key={index} className="font-semibold">{parts}</h4>;
    if (bullet) return <div key={index} className="pl-4 list-item list-disc">{parts}</div>;
    if (numbered) return <div key={index} className="pl-4 list-item list-decimal">{parts}</div>;
    return <p key={index}>{parts}</p>;
  })}</div>;
};
