import React from 'react';
import { Sparkles, Link as LinkIcon, User } from 'lucide-react';

export default function MessageBubble({ role, content, citationUrl, lastUpdated, isGenerating }) {
  const isUser = role === 'user';

  // Helper to format bold text (**text**) and split lines/paragraphs safely
  const formatContent = (text) => {
    if (!text) return '';
    
    // Split text into lines to handle paragraphs and bullet points
    const lines = text.split('\n');
    
    return lines.map((line, lineIndex) => {
      // Check if line is a bullet point (starts with '-' or '*')
      const isBullet = line.trim().startsWith('-') || line.trim().startsWith('*');
      const cleanLine = isBullet ? line.trim().substring(1).trim() : line;

      // Replace **text** with <strong>text</strong>
      const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
      const formattedLine = parts.map((part, partIndex) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={partIndex} className="text-primary font-bold">{part.slice(2, -2)}</strong>;
        }
        return part;
      });

      if (isBullet) {
        return (
          <li key={lineIndex} className="ml-5 list-disc leading-relaxed text-text-primary mb-1">
            {formattedLine}
          </li>
        );
      }

      return (
        <p key={lineIndex} className="leading-relaxed text-text-primary mb-2 min-h-[1.5rem]">
          {formattedLine}
        </p>
      );
    });
  };

  const getCleanCitationText = (url) => {
    if (!url) return '';
    try {
      const parsed = new URL(url);
      // return paths like groww.in/mutual-funds/...
      return parsed.hostname + parsed.pathname;
    } catch {
      return 'groww.in/mutual-funds';
    }
  };

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      {isUser ? (
        /* User Message Bubble */
        <div className="max-w-[85%] bg-primary/10 border border-primary/30 p-4 rounded-2xl rounded-tr-sm shadow-sm flex gap-3 items-start">
          <div className="flex-1">
            <div className="text-primary font-sans text-body-md leading-relaxed whitespace-pre-wrap">
              {content}
            </div>
          </div>
          <div className="w-6 h-6 rounded-full bg-primary/25 border border-primary/50 flex items-center justify-center shrink-0">
            <User className="w-3.5 h-3.5 text-primary" />
          </div>
        </div>
      ) : (
        /* Assistant Message Bubble */
        <div className="max-w-[90%] md:max-w-[800px] glass-panel p-5 rounded-2xl rounded-tl-sm shadow-md flex flex-col w-full">
          {/* Header */}
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
            </div>
            <span className="font-headline text-xs font-bold text-primary tracking-wider uppercase">
              Assistant Response
            </span>
          </div>

          {/* Body Content */}
          <div className="text-text-primary text-sm space-y-1">
            {isGenerating && !content ? (
              /* Typing / Thinking Loader Animation */
              <div className="flex items-center gap-1.5 py-2">
                <span className="text-text-secondary italic text-xs mr-1">Generating answer...</span>
                <span className="w-1.5 h-1.5 rounded-full bg-primary dot-bounce-1"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-primary dot-bounce-2"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-primary dot-bounce-3"></span>
              </div>
            ) : (
              formatContent(content)
            )}
          </div>

          {/* Citation Footer (only for valid responses with source URLs) */}
          {citationUrl && !isGenerating && (
            <div className="flex flex-wrap items-center gap-4 pt-3 mt-3 border-t border-glass-border">
              <a 
                href={citationUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-background/50 border border-glass-border text-xs text-text-secondary hover:text-primary hover:border-primary/50 transition-all shadow-sm"
              >
                <LinkIcon className="w-3 h-3 text-primary" />
                <span className="truncate max-w-[200px] md:max-w-xs">{getCleanCitationText(citationUrl)}</span>
              </a>
              {lastUpdated && (
                <span className="text-[10px] uppercase font-semibold text-text-secondary tracking-wider opacity-65">
                  Last Scraped: {lastUpdated}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
