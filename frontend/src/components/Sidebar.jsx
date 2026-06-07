import React, { useState } from 'react';
import { 
  Plus, MessageSquare, Trash2, Edit2, Check, X, 
  Settings, HelpCircle, Archive, Menu, TrendingUp
} from 'lucide-react';

export default function Sidebar({ 
  sessions, 
  currentSessionId, 
  onLoadSession, 
  onCreateSession, 
  onDeleteSession, 
  onRenameSession,
  isSidebarOpen,
  setIsSidebarOpen
}) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const startEditing = (e, id, currentTitle) => {
    e.stopPropagation();
    setEditingId(id);
    setEditTitle(currentTitle);
  };

  const cancelEditing = (e) => {
    e.stopPropagation();
    setEditingId(null);
    setEditTitle('');
  };

  const saveRename = (e, id) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside 
        className={`fixed left-0 top-0 h-full bg-surface-elevated border-r border-glass-border flex flex-col z-50 transition-all duration-300
          ${isSidebarOpen ? 'w-[280px] translate-x-0' : 'w-0 -translate-x-full lg:w-[72px] lg:translate-x-0'}
        `}
      >
        {/* Sidebar Header */}
        <div className={`p-6 border-b border-glass-border flex flex-col gap-6 ${isSidebarOpen ? 'block' : 'items-center lg:py-6 lg:px-2'}`}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-lg accent-shadow shrink-0">
              <TrendingUp className="text-background font-bold w-5 h-5" />
            </div>
            {isSidebarOpen && (
              <div>
                <h1 className="font-headline text-lg font-bold text-primary tracking-tight">AlphaWealth</h1>
                <p className="font-sans text-xs text-text-secondary font-medium">Premium RAG</p>
              </div>
            )}
          </div>
          
          <button 
            onClick={() => {
              onCreateSession();
              // Close on mobile
              if (window.innerWidth < 1024) {
                setIsSidebarOpen(false);
              }
            }}
            className={`flex items-center justify-center bg-primary text-background font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-primary/25 hover:bg-primary-hover
              ${isSidebarOpen ? 'w-full gap-2 py-3 px-4' : 'w-10 h-10 p-0'}
            `}
            title="Start New Chat"
          >
            <Plus className="w-5 h-5 shrink-0" />
            {isSidebarOpen && <span>New Chat</span>}
          </button>
        </div>

        {/* Chat History List */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-2">
          {isSidebarOpen && (
            <p className="text-[10px] uppercase font-bold text-text-secondary tracking-widest pl-3 mb-2 opacity-60">
              Chat History
            </p>
          )}

          {sessions.length === 0 ? (
            isSidebarOpen && (
              <p className="text-xs text-text-secondary text-center italic py-4 opacity-55">
                No past sessions
              </p>
            )
          ) : (
            sessions.map((session) => {
              const isActive = session.id === currentSessionId;
              const isEditing = session.id === editingId;

              return (
                <div
                  key={session.id}
                  onClick={() => {
                    if (!isEditing) {
                      onLoadSession(session.id);
                      if (window.innerWidth < 1024) {
                        setIsSidebarOpen(false);
                      }
                    }
                  }}
                  className={`group flex items-center gap-3 rounded-xl transition-all duration-200 cursor-pointer relative
                    ${isSidebarOpen ? 'px-4 py-3' : 'justify-center w-10 h-10 p-0 mx-auto'}
                    ${isActive && isSidebarOpen ? 'border-l-4 border-primary bg-primary/10 text-primary' : 'text-text-secondary hover:bg-surface-card hover:text-text-primary'}
                  `}
                >
                  <MessageSquare className="w-4 h-4 shrink-0" />
                  
                  {isSidebarOpen && (
                    <div className="flex-1 min-w-0 pr-4">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveRename(e, session.id);
                            if (e.key === 'Escape') cancelEditing(e);
                          }}
                          className="w-full bg-surface-container border border-primary/50 text-text-primary text-sm rounded px-1 focus:outline-none focus:ring-1 focus:ring-primary"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <p className="text-sm font-medium truncate leading-none">
                          {session.title || "Untitled Session"}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Hover Actions (Edit / Delete) */}
                  {isSidebarOpen && isActive && !isEditing && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-l from-surface-elevated via-surface-elevated pl-4">
                      <button 
                        onClick={(e) => startEditing(e, session.id, session.title)}
                        className="p-1 hover:text-primary transition-colors"
                        title="Rename chat"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                        className="p-1 hover:text-red-400 transition-colors"
                        title="Delete chat"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {isEditing && isSidebarOpen && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 bg-surface-elevated">
                      <button 
                        onClick={(e) => saveRename(e, session.id)}
                        className="p-0.5 hover:text-primary transition-colors"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button 
                        onClick={(e) => cancelEditing(e)}
                        className="p-0.5 hover:text-red-400 transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </nav>

        {/* Sidebar Footer */}
        <div className={`p-4 border-t border-glass-border space-y-1 flex flex-col ${isSidebarOpen ? 'block' : 'items-center'}`}>
          <button className={`flex items-center text-text-secondary hover:bg-surface-card hover:text-text-primary transition-all rounded-lg w-full py-2.5 px-3
            ${isSidebarOpen ? 'gap-3' : 'justify-center w-10 h-10 p-0'}
          `} title="Help & Support">
            <HelpCircle className="w-4 h-4 shrink-0" />
            {isSidebarOpen && <span className="text-sm font-medium">Support</span>}
          </button>
          <button className={`flex items-center text-text-secondary hover:bg-surface-card hover:text-text-primary transition-all rounded-lg w-full py-2.5 px-3
            ${isSidebarOpen ? 'gap-3' : 'justify-center w-10 h-10 p-0'}
          `} title="Archive">
            <Archive className="w-4 h-4 shrink-0" />
            {isSidebarOpen && <span className="text-sm font-medium">Archive</span>}
          </button>
          <button className={`flex items-center text-text-secondary hover:bg-surface-card hover:text-text-primary transition-all rounded-lg w-full py-2.5 px-3
            ${isSidebarOpen ? 'gap-3' : 'justify-center w-10 h-10 p-0'}
          `} title="Settings">
            <Settings className="w-4 h-4 shrink-0" />
            {isSidebarOpen && <span className="text-sm font-medium">Settings</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
