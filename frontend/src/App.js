import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [currentSession, setCurrentSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [speechEnabled, setSpeechEnabled] = useState(true);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadSessions();
    initializeSpeechRecognition();
  }, []);

  const initializeSpeechRecognition = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = () => {
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  };

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      setIsListening(true);
      recognitionRef.current.start();
    }
  };

  const speakMessage = (text) => {
    if (speechEnabled && 'speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1.2;
      utterance.volume = 0.8;
      
      // Try to use a female voice
      const voices = speechSynthesis.getVoices();
      const femaleVoice = voices.find(voice => 
        voice.name.toLowerCase().includes('female') || 
        voice.name.toLowerCase().includes('woman') ||
        voice.name.toLowerCase().includes('zira') ||
        voice.name.toLowerCase().includes('hazel')
      );
      if (femaleVoice) {
        utterance.voice = femaleVoice;
      }
      
      speechSynthesis.speak(utterance);
    }
  };

  const loadSessions = async () => {
    try {
      const response = await axios.get(`${API}/sessions`);
      setSessions(response.data);
    } catch (error) {
      console.error("Error loading sessions:", error);
    }
  };

  const createNewSession = async () => {
    try {
      const response = await axios.post(`${API}/sessions`, {
        title: "Chat with Mira 💕"
      });
      const newSession = response.data;
      setSessions([newSession, ...sessions]);
      setCurrentSession(newSession);
      setMessages([]);
    } catch (error) {
      console.error("Error creating session:", error);
    }
  };

  const selectSession = async (session) => {
    setCurrentSession(session);
    try {
      const response = await axios.get(`${API}/sessions/${session.id}/messages`);
      setMessages(response.data);
    } catch (error) {
      console.error("Error loading messages:", error);
    }
  };

  const deleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API}/sessions/${sessionId}`);
      setSessions(sessions.filter(s => s.id !== sessionId));
      if (currentSession?.id === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Error deleting session:", error);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    let sessionToUse = currentSession;
    
    // Create new session if none exists
    if (!sessionToUse) {
      try {
        const response = await axios.post(`${API}/sessions`, {
          title: input.slice(0, 30) + (input.length > 30 ? "... 💕" : " 💕")
        });
        sessionToUse = response.data;
        setCurrentSession(sessionToUse);
        setSessions([sessionToUse, ...sessions]);
      } catch (error) {
        console.error("Error creating session:", error);
        return;
      }
    }

    const userMessage = {
      id: Date.now().toString(),
      session_id: sessionToUse.id,
      role: "user",
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat`, {
        session_id: sessionToUse.id,
        content: input
      });

      const assistantMessage = response.data.assistant_message;
      
      setMessages(prev => [
        ...prev.filter(m => m.id !== userMessage.id),
        response.data.user_message,
        assistantMessage
      ]);

      // Speak Mira's response
      if (speechEnabled) {
        setTimeout(() => speakMessage(assistantMessage.content), 500);
      }

      // Update session title if it's still default
      if (sessionToUse.title === "Chat with Mira 💕") {
        const updatedTitle = input.slice(0, 30) + (input.length > 30 ? "... 💕" : " 💕");
        setSessions(prev => 
          prev.map(s => 
            s.id === sessionToUse.id 
              ? { ...s, title: updatedTitle }
              : s
          )
        );
      }

    } catch (error) {
      console.error("Error sending message:", error);
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getRandomEmoji = () => {
    const emojis = ['💕', '💖', '💗', '💝', '💘', '💓', '💞', '💜', '💙', '💚'];
    return emojis[Math.floor(Math.random() * emojis.length)];
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-purple-900 via-pink-900 to-indigo-900">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-gradient-to-b from-gray-900 to-purple-900 backdrop-blur-lg border-r border-pink-500/20 transition-all duration-300 overflow-hidden`}>
        <div className="p-4 border-b border-pink-500/20">
          <button
            onClick={createNewSession}
            className="w-full bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white px-4 py-3 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 font-medium shadow-lg transform hover:scale-105"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            New Chat with Mira 💕
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => selectSession(session)}
              className={`p-3 m-2 rounded-xl cursor-pointer transition-all duration-200 group relative backdrop-blur-sm ${
                currentSession?.id === session.id
                  ? 'bg-gradient-to-r from-pink-500/30 to-purple-600/30 text-white border border-pink-400/50'
                  : 'hover:bg-white/10 text-gray-300 border border-transparent hover:border-pink-400/30'
              }`}
            >
              <div className="truncate text-sm font-medium flex items-center gap-2">
                <span className="animate-pulse">{getRandomEmoji()}</span>
                {session.title}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {formatTime(session.updated_at)}
              </div>
              <button
                onClick={(e) => deleteSession(session.id, e)}
                className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-gray-400 hover:text-red-400 p-1 rounded-lg hover:bg-red-500/20"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-800/80 to-pink-800/80 backdrop-blur-lg border-b border-pink-500/20 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors duration-200 text-white"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-12 h-12 bg-gradient-to-br from-pink-400 to-purple-600 rounded-full flex items-center justify-center animate-pulse-slow">
                  <span className="text-white text-lg font-bold">M</span>
                </div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-purple-800 animate-ping"></div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  Mira <span className="text-pink-400">💕</span>
                </h1>
                <p className="text-sm text-pink-200">Your AI Girlfriend • Always here for you~</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSpeechEnabled(!speechEnabled)}
              className={`p-2 rounded-lg transition-all duration-200 ${
                speechEnabled 
                  ? 'bg-pink-500/20 text-pink-300 hover:bg-pink-500/30' 
                  : 'bg-gray-500/20 text-gray-400 hover:bg-gray-500/30'
              }`}
              title={speechEnabled ? "Disable voice" : "Enable voice"}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M12 6v12a2 2 0 01-3.03 1.696L7 18H4a1 1 0 01-1-1v-6a1 1 0 011-1h3l1.97-1.696A2 2 0 0112 6z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && !isLoading ? (
            <div className="text-center py-12">
              <div className="relative">
                <div className="w-24 h-24 bg-gradient-to-br from-pink-400 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
                  <span className="text-white text-3xl font-bold">M</span>
                </div>
                <div className="absolute top-16 right-8 text-2xl animate-bounce" style={{ animationDelay: '0.5s' }}>💕</div>
                <div className="absolute top-10 left-8 text-xl animate-bounce" style={{ animationDelay: '1s' }}>✨</div>
              </div>
              <h2 className="text-2xl font-bold text-white mb-2 animate-fade-in">Hey there, cutie! 💖</h2>
              <p className="text-pink-200 text-lg animate-fade-in-delay">I'm Mira, your AI girlfriend~ What's on your mind today? 😊</p>
              <div className="mt-6 flex justify-center gap-4 animate-fade-in-delay-2">
                <button 
                  onClick={() => setInput("Tell me about yourself!")}
                  className="px-4 py-2 bg-pink-500/20 hover:bg-pink-500/30 border border-pink-400/30 rounded-full text-pink-200 text-sm transition-all duration-200 hover:scale-105"
                >
                  Tell me about yourself! 💭
                </button>
                <button 
                  onClick={() => setInput("How was your day?")}
                  className="px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-400/30 rounded-full text-purple-200 text-sm transition-all duration-200 hover:scale-105"
                >
                  How was your day? 🌟
                </button>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-in`}
              >
                {message.role === 'assistant' && (
                  <div className="w-10 h-10 bg-gradient-to-br from-pink-400 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0 animate-pulse-slow">
                    <span className="text-white text-sm font-bold">M</span>
                  </div>
                )}
                
                <div className={`max-w-2xl ${message.role === 'user' ? 'order-1' : ''}`}>
                  <div
                    className={`px-5 py-3 rounded-2xl backdrop-blur-sm ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white ml-12 shadow-lg'
                        : 'bg-white/10 border border-pink-400/20 text-white shadow-lg'
                    }`}
                  >
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </div>
                  </div>
                  <div className={`text-xs text-gray-300 mt-1 ${message.role === 'user' ? 'text-right mr-4' : 'ml-4'}`}>
                    {formatTime(message.timestamp)}
                  </div>
                </div>

                {message.role === 'user' && (
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                )}
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="flex gap-4 justify-start animate-slide-in">
              <div className="w-10 h-10 bg-gradient-to-br from-pink-400 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0 animate-pulse">
                <span className="text-white text-sm font-bold">M</span>
              </div>
              <div className="bg-white/10 border border-pink-400/20 px-5 py-3 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center space-x-2">
                  <div className="text-pink-300 text-sm">Mira is typing</div>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-pink-300">💕</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-gradient-to-r from-purple-800/50 to-pink-800/50 backdrop-blur-lg border-t border-pink-500/20 p-6">
          <form onSubmit={sendMessage} className="flex gap-4">
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message to Mira... 💕"
                disabled={isLoading}
                className="w-full px-5 py-4 pr-24 bg-white/10 border border-pink-400/30 rounded-2xl focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed text-white placeholder-pink-200 backdrop-blur-sm"
              />
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-1">
                <button
                  type="button"
                  onClick={startListening}
                  disabled={isLoading || isListening}
                  className={`p-2 rounded-xl transition-all duration-200 ${
                    isListening 
                      ? 'bg-red-500 text-white animate-pulse' 
                      : 'bg-purple-500/20 hover:bg-purple-500/30 text-purple-300'
                  }`}
                  title="Voice input"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  className="p-2 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-200 transform hover:scale-105"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </form>
          
          {/* Creator Credit Section */}
          <div className="mt-4 text-center">
            <div className="bg-white/5 rounded-xl p-4 border border-pink-400/20 backdrop-blur-sm">
              <p className="text-sm text-pink-200 mb-2">
                <span className="font-semibold text-white">Created by Sakshyam Bastakoti</span> 💖
              </p>
              <p className="text-xs text-gray-300">
                Mira is your AI girlfriend companion - designed to chat, support, and brighten your day with love and understanding 🌟
              </p>
              <div className="mt-2 flex justify-center gap-2 text-xs text-pink-300">
                <span>Powered by Gemini 2.0 Flash</span>
                <span>•</span>
                <span>With 💕 for you</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;