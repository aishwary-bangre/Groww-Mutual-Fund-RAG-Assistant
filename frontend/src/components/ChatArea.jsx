import React, { useRef, useEffect, useState } from 'react';
import { Send, Info, ArrowRight, Activity } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatArea({ 
  messages, 
  onSendMessage, 
  isGenerating,
  onNewSession
}) {
  const [queryText, setQueryText] = useState('');
  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 192)}px`;
    }
  }, [queryText]);

  // Scroll to bottom on new messages or generation states
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const cleanQuery = queryText.trim();
    if (!cleanQuery || isGenerating) return;
    
    onSendMessage(cleanQuery);
    setQueryText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const triggerSuggestion = (text) => {
    onSendMessage(text);
  };

  const suggestions = [
    "What is the exit load of HDFC Mid Cap Fund?",
    "Who manages Parag Parikh Long Term Value Fund?",
    "What is the minimum SIP for Motilal Oswal?"
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden relative">
      {/* Messages Viewport */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 md:px-6 py-6 scroll-smooth pb-36"
      >
        {messages.length === 0 ? (
          /* Welcome State (Empty Chat) */
          <div className="max-w-[800px] mx-auto mt-12 flex flex-col items-center text-center">
            <div className="mb-6 p-5 rounded-3xl bg-primary/5 border border-primary/20 accent-shadow text-primary flex items-center justify-center">
              <Activity className="w-12 h-12" />
            </div>
            <h3 className="font-headline text-3xl md:text-4xl text-text-primary font-bold mb-3 tracking-tight">
              How can I help with your Groww Portfolio?
            </h3>
            <p className="font-sans text-sm md:text-base text-text-secondary mb-10 max-w-xl leading-relaxed">
              I am your AI financial companion, specializing in real-time Mutual Fund insights directly retrieved from public Groww market documents.
            </p>

            {/* Disclaimer Banner */}
            <div className="mb-10 w-full p-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 flex items-start gap-3.5 text-left shadow-sm">
              <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <p className="font-headline text-xs font-bold text-amber-500 uppercase tracking-widest mb-1">
                  Compliance Disclaimer
                </p>
                <p className="font-sans text-xs text-text-secondary leading-relaxed font-medium">
                  This assistant provides factual educational details extracted directly from Groww mutual fund pages. It is NOT a SEBI-registered advisory service and does NOT provide financial recommendation, opinions, or investment advice. Mutual fund investments are subject to market risks.
                </p>
              </div>
            </div>

            {/* Suggestion Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
              {suggestions.map((text, idx) => (
                <button 
                  key={idx}
                  onClick={() => triggerSuggestion(text)}
                  className="glass-panel p-5 rounded-2xl text-left hover:border-primary/40 hover:bg-surface-card/60 transition-all duration-300 group flex flex-col justify-between min-h-[140px] shadow-sm active:scale-[0.98]"
                >
                  <p className="font-sans text-sm font-semibold text-text-primary group-hover:text-primary transition-colors leading-relaxed">
                    {text}
                  </p>
                  <div className="flex justify-between items-center w-full mt-4">
                    <span className="text-[10px] uppercase font-bold text-text-secondary tracking-wider opacity-60">
                      Query suggestion
                    </span>
                    <ArrowRight className="w-4 h-4 text-text-secondary group-hover:text-primary group-hover:translate-x-1 transition-all" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Active Chat Messages */
          <div className="max-w-[800px] mx-auto space-y-6">
            {messages.map((msg, index) => (
              <MessageBubble 
                key={index}
                role={msg.role}
                content={msg.content}
                citationUrl={msg.citation_url}
                lastUpdated={msg.last_updated}
                isGenerating={false}
              />
            ))}
            
            {/* Generate loading bubble */}
            {isGenerating && (
              <MessageBubble 
                role="assistant"
                content=""
                isGenerating={true}
              />
            )}
            
            {/* Anchor for scrolling */}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Input Area */}
      <div className="absolute bottom-0 left-0 w-full p-4 md:p-6 bg-gradient-to-t from-background via-background/95 to-transparent">
        <div className="max-w-[800px] mx-auto relative group">
          <form onSubmit={handleSubmit} className="glass-panel rounded-2xl flex items-end gap-2 p-3 shadow-2xl focus-within:border-primary/50 transition-all duration-350">
            <textarea
              ref={textareaRef}
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about scheme exit loads, expense ratios, AUM, or managers..."
              rows={1}
              disabled={isGenerating}
              className="w-full bg-transparent border-none outline-none focus:ring-0 focus:border-none text-text-primary placeholder:text-text-secondary/60 resize-none py-2 px-3 max-h-48 text-sm focus:outline-none focus:ring-transparent focus:shadow-none"
              style={{ scrollbarWidth: 'none' }}
            />
            <button
              type="submit"
              disabled={!queryText.trim() || isGenerating}
              className="bg-primary hover:brightness-110 active:scale-95 transition-all p-3 rounded-xl flex items-center justify-center text-background shadow-lg shadow-primary/20 disabled:opacity-40 disabled:pointer-events-none shrink-0"
            >
              <Send className="w-4 h-4 font-bold" />
            </button>
          </form>
          <p className="text-[10px] text-center mt-3 text-text-secondary uppercase tracking-widest opacity-60 font-semibold">
            AI model may produce inaccuracies. Cross-verify details with official scheme documents.
          </p>
        </div>
      </div>
    </div>
  );
}
