import React, { useState, useEffect } from 'react';
import { Menu, Wifi, WifiOff, Bell, User as UserIcon } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function App() {
  const [sessions, setSessions] = useState(() => {
    const cached = localStorage.getItem('alphawealth_sessions');
    return cached ? JSON.parse(cached) : [];
  });
  
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    const cached = localStorage.getItem('alphawealth_sessions');
    const list = cached ? JSON.parse(cached) : [];
    return list.length > 0 ? list[0].id : null;
  });

  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth >= 1024);
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'
  const [isGenerating, setIsGenerating] = useState(false);

  // Sync sessions to localStorage
  useEffect(() => {
    localStorage.setItem('alphawealth_sessions', JSON.stringify(sessions));
  }, [sessions]);

  // Check backend health on startup
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        const data = await res.json();
        if (data.status === 'healthy') {
          setBackendStatus('connected');
        } else {
          setBackendStatus('disconnected');
        }
      } catch (err) {
        console.error('Health check failed:', err);
        setBackendStatus('disconnected');
      }
    };
    checkHealth();
  }, []);

  // Handle window resizing to toggle sidebar collapse state
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsSidebarOpen(true);
      } else {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleCreateSession = (initialQuery = null) => {
    const id = Date.now().toString();
    const title = initialQuery 
      ? (initialQuery.length > 30 ? initialQuery.substring(0, 30) + '...' : initialQuery)
      : 'New Analysis Session';

    const newSession = {
      id,
      title,
      messages: []
    };

    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(id);
    return id;
  };

  const handleLoadSession = (id) => {
    setCurrentSessionId(id);
  };

  const handleDeleteSession = (id) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (currentSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      setCurrentSessionId(remaining.length > 0 ? remaining[0].id : null);
    }
  };

  const handleRenameSession = (id, newTitle) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, title: newTitle } : s));
  };

  const handleSendMessage = async (queryText) => {
    let activeId = currentSessionId;
    
    // Create new session if none is currently active
    if (!activeId) {
      activeId = handleCreateSession(queryText);
    }

    const userMessage = {
      role: 'user',
      content: queryText
    };

    // Optimistically update local session messages
    setSessions(prev => prev.map(s => {
      if (s.id === activeId) {
        const updatedMessages = [...s.messages, userMessage];
        const updatedTitle = s.messages.length === 0 ? (queryText.length > 30 ? queryText.substring(0, 30) + '...' : queryText) : s.title;
        return {
          ...s,
          title: updatedTitle,
          messages: updatedMessages
        };
      }
      return s;
    }));

    setIsGenerating(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: queryText })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        citation_url: data.citation_url,
        last_updated: data.last_updated,
        intent: data.intent
      };

      setSessions(prev => prev.map(s => {
        if (s.id === activeId) {
          return {
            ...s,
            messages: [...s.messages, assistantMessage]
          };
        }
        return s;
      }));

    } catch (error) {
      console.error('Error fetching chat response:', error);
      
      const errorMessage = {
        role: 'assistant',
        content: `⚠️ Failed to get a response from the backend. Please check that the server is running at ${API_BASE_URL} and try again.`
      };

      setSessions(prev => prev.map(s => {
        if (s.id === activeId) {
          return {
            ...s,
            messages: [...s.messages, errorMessage]
          };
        }
        return s;
      }));
    } finally {
      setIsGenerating(false);
    }
  };

  const activeSession = sessions.find(s => s.id === currentSessionId);
  const activeMessages = activeSession ? activeSession.messages : [];

  return (
    <div className="flex h-screen overflow-hidden text-body-md text-text-primary bg-background font-sans">
      
      {/* Collapsible Sidebar */}
      <Sidebar 
        sessions={sessions}
        currentSessionId={currentSessionId}
        onLoadSession={handleLoadSession}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
      />

      {/* Main Panel Canvas */}
      <main className={`flex-1 flex flex-col h-full bg-background transition-all duration-300
        ${isSidebarOpen ? 'lg:ml-[280px]' : 'lg:ml-[72px]'}
      `}>
        {/* Top App Header */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-glass-border bg-background/80 backdrop-blur-xl sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 text-text-secondary hover:text-primary transition-colors hover:bg-surface-card rounded-lg"
              title="Toggle Sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <h2 className="font-headline text-lg md:text-xl font-bold text-primary tracking-tight">
                Groww RAG Assistant
              </h2>
              {backendStatus === 'connected' && (
                <div className="w-2 h-2 rounded-full bg-primary pulse-green ml-1" />
              )}
            </div>
          </div>
          
          {/* Header Status & User */}
          <div className="flex items-center gap-4">
            {/* Health Indicators */}
            <div className="hidden md:flex bg-surface-elevated border border-glass-border px-3 py-1.5 rounded-full items-center gap-2">
              {backendStatus === 'connected' ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-primary" />
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
                    Connected
                  </span>
                </>
              ) : backendStatus === 'checking' ? (
                <>
                  <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
                    Pinging API...
                  </span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-red-400" />
                  <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">
                    Disconnected
                  </span>
                </>
              )}
            </div>

            <button className="text-text-secondary hover:text-primary transition-colors p-1.5 hover:bg-surface-card rounded-lg">
              <Bell className="w-4 h-4" />
            </button>

            <div className="w-8 h-8 rounded-full bg-surface-card border border-glass-border flex items-center justify-center shadow-md cursor-pointer hover:border-primary/50 transition-colors">
              <UserIcon className="w-4 h-4 text-text-secondary" />
            </div>
          </div>
        </header>

        {/* Dynamic Workspace (Chat area or welcome screen) */}
        <ChatArea 
          messages={activeMessages}
          onSendMessage={handleSendMessage}
          isGenerating={isGenerating}
          onNewSession={() => handleCreateSession()}
        />
      </main>
    </div>
  );
}
