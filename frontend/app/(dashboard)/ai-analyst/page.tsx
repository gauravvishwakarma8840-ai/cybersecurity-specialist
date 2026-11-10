'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { aiApi } from '@/lib/api';
import styles from './page.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

const QUICK_PROMPTS = [
  'Explain MITRE ATT&CK technique T1059',
  'What are indicators of ransomware infection?',
  'How should I respond to a brute force attack?',
  'What is lateral movement in a cyberattack?',
  'Explain the NIST Cybersecurity Framework',
  'What logs should I monitor for account compromise?',
];

export default function AIAnalystPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState<{ session_id: string; title: string; updated_at: string }[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function loadConversations() {
    try {
      const convs = await aiApi.getConversations();
      setConversations(convs);
    } catch {}
  }

  async function loadConversation(sid: string) {
    try {
      const conv = await aiApi.getConversation(sid);
      setMessages(conv.messages as Message[]);
      setSessionId(sid);
    } catch {}
  }

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;
    setInput('');

    const userMsg: Message = { role: 'user', content, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await aiApi.chat(content, sessionId);
      setSessionId(res.session_id);
      const aiMsg: Message = { role: 'assistant', content: res.message, timestamp: res.timestamp };
      setMessages(prev => [...prev, aiMsg]);
      loadConversations();
    } catch (err) {
      const errMsg: Message = {
        role: 'assistant',
        content: '⚠️ Unable to reach the AI service. Please check your connection and try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [isLoading, sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setSessionId(undefined);
    setInput('');
  };

  return (
    <div className={styles.page}>
      {/* Sidebar: Conversations */}
      <aside className={styles.convSidebar}>
        <div className={styles.convHeader}>
          <h3>Conversations</h3>
          <button className="btn btn--primary btn--sm" onClick={startNewChat}>+ New</button>
        </div>
        <div className={styles.convList}>
          {conversations.length === 0 ? (
            <p className="text-sm text-muted" style={{ padding: '12px' }}>No conversations yet</p>
          ) : (
            conversations.map(c => (
              <button
                key={c.session_id}
                className={`${styles.convItem} ${sessionId === c.session_id ? styles.convItemActive : ''}`}
                onClick={() => loadConversation(c.session_id)}
              >
                <span className={styles.convTitle}>{c.title || 'Conversation'}</span>
                <span className={styles.convDate}>{new Date(c.updated_at).toLocaleDateString()}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className={styles.chatArea}>
        {/* Welcome State */}
        {messages.length === 0 && (
          <div className={styles.welcome}>
            <div className={styles.welcomeIcon}>🛡️</div>
            <h2>CyberSentinel AI Analyst</h2>
            <p>Your AI-powered security expert. Ask me anything about threats, incidents, CVEs, or security best practices.</p>
            <div className={styles.quickPromptsGrid}>
              {QUICK_PROMPTS.map(prompt => (
                <button key={prompt} className={styles.quickPrompt} onClick={() => sendMessage(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className={styles.messages}>
          {messages.map((msg, i) => (
            <div key={i} className={`${styles.message} ${styles[`message--${msg.role}`]}`}>
              <div className={styles.messageAvatar}>
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className={styles.messageBubble}>
                <div className={styles.messageContent}>
                  {msg.content.split('\n').map((line, j) => (
                    <span key={j}>{line}<br /></span>
                  ))}
                </div>
                <div className={styles.messageTime}>
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className={`${styles.message} ${styles['message--assistant']}`}>
              <div className={styles.messageAvatar}>🤖</div>
              <div className={styles.messageBubble}>
                <div className={styles.typingIndicator}>
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input Area */}
        <div className={styles.inputArea}>
          <textarea
            ref={inputRef}
            className={styles.chatInput}
            placeholder="Ask the AI Analyst anything... (Shift+Enter for new line)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button
            className={`btn btn--primary ${styles.sendBtn}`}
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
            aria-label="Send message"
          >
            {isLoading ? <span className="animate-spin">⟳</span> : '→'}
          </button>
        </div>
      </div>
    </div>
  );
}
