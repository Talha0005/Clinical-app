import { useState, useRef, useCallback, useEffect } from "react";
import { MedicalHeader } from "./MedicalHeader";
import { MedicalDisclaimer } from "./MedicalDisclaimer";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { useAuth } from "../hooks/useAuth";
import { apiFetch } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import { AvatarBubble } from "./AvatarBubble";

interface Message {
  id: string;
  content: string;
  sender: "doctor" | "user";
  timestamp: string;
  avatar?: string;
  clinicalCodes?: Array<{ code: string; system: string; display: string }>;
}

export const DigiClinic = () => {
  const { token } = useAuth();
  // Local, non-breaking flags
  const SHOW_CODES_FOR_CHAT = true; // attach codes to doctor replies for typed chat
  const DEFAULT_AVATAR = "dr_hervix"; // seed for doctor avatar image
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Good afternoon! I'm Dr. Hervix, your digital GP consultant. I'm here to help you with any medical concerns you may have. Before we begin, please note that this is a consultation tool to help assess your symptoms and provide guidance. For emergencies, please call 999 immediately. How can I help you today?",
      sender: "doctor",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      // Ensure the initial doctor message has an avatar seed
      avatar: DEFAULT_AVATAR,
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const conversationIdRef = useRef<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [assistantSpeaking, setAssistantSpeaking] = useState<boolean>(false);
  const [userSpeaking, setUserSpeaking] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);

  // Model selection state
  // Align with backend enum ModelProvider values (use supported Sonnet ID: 20240620)
  const [currentModel, setCurrentModel] = useState<string>("anthropic/claude-3-5-sonnet-20240620");

  useEffect(() => {
    const fetchCurrentModel = async () => {
      try {
        const response = await apiFetch("/api/models/current", { auth: true, token });
        if (response.ok) {
          const data = await response.json();
          setCurrentModel(data.model);
        }
      } catch (error) {
        console.error("Failed to fetch current model:", error);
      }
    };

    if (token) {
      fetchCurrentModel();
    }
  }, [token]);

  // Handle model selection
  const handleModelSelect = async (modelId: string) => {
    // No-op if selecting the current model
    if (modelId === currentModel) {
      toast({ title: 'Model already selected', description: `${modelId} is already active.` });
      return;
    }
    try {
      // Switch to the new model via API
      const response = await apiFetch('/api/models/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        auth: true,
        token,
        body: JSON.stringify({
          model_id: modelId,
          conversation_id: conversationId || 'default',
          reason: 'User requested model switch'
        })
      });

      const result = await response.json().catch(() => null);
      if (!response.ok || !result?.success) {
        const detail =
          result?.detail ||
          result?.error ||
          (Array.isArray(result) && result[0]?.msg) ||
          `Failed to switch to ${modelId}`;
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        // Surface clearer guidance for disabled/unavailable models
        if (response.status === 400) {
          throw new Error(message.includes('disabled') || message.includes('not available')
            ? `${message}. Please choose another model.`
            : message);
        }
        throw new Error(message);
      }

      setCurrentModel(modelId);

      // Add a system message to show the model switch
      const switchMessage: Message = {
        id: Date.now().toString(),
        content: `🔄 Switched to ${result.message || modelId}. How can I continue to help you?`,
        sender: "doctor",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, switchMessage]);
    } catch (error: any) {
      console.error('Failed to switch model:', error);
      toast({
        title: 'Model switch failed',
        description: error?.message || 'Please choose a different model or try again.',
        variant: 'destructive'
      });
    }
  };

  const handleVoiceAIResponse = useCallback((response: string, meta?: any) => {
    // Add AI response message from voice input
    const aiMessage: Message = {
      id: Date.now().toString(),
      content: `🎤 ${response}`,
      sender: "doctor",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      avatar: meta?.avatar,
      clinicalCodes: Array.isArray(meta?.clinical?.codes) ? meta.clinical.codes : undefined,
    };

    setMessages(prev => [...prev, aiMessage]);
    
    // Show that the AI has responded to voice
    toast({
      title: "Voice AI Response",
      description: "Dr. Hervix has responded to your voice message",
    });
  }, []);

  const handleSendMessage = useCallback(async (content: string) => {
    if (sending) return; // prevent overlapping sends
    setSending(true);
    // Basic guard: ignore accidental empty/whitespace messages
    if (!content || !content.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      sender: "user",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    try {
      // Use token from auth context
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Create a placeholder message for streaming response
      const streamingMessageId = (Date.now() + 1).toString();
      const streamingMessage: Message = {
        id: streamingMessageId,
        content: "",
        sender: "doctor",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        avatar: DEFAULT_AVATAR,
      };
      
      setMessages(prev => [...prev, streamingMessage]);
  setIsTyping(false);
  setAssistantSpeaking(true);

      // Use the model selection API with streaming
      const response = await apiFetch('/api/models/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        auth: true,
        token,
        timeoutMs: 120_000,
        body: JSON.stringify({
          message: content,
          conversation_id: conversationId || 'default',
          model_id: currentModel
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      let lastChunkAt = Date.now();

      // Optional: timeout if stream stalls for too long
      const STREAM_TIMEOUT_MS = 60_000;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        lastChunkAt = Date.now();
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith('data:')) {
            try {
              const payload = trimmed.slice(5).trim();
              if (!payload) continue;
              const data = JSON.parse(payload);
              
              if (data.type === 'start' && data.conversation_id && !conversationIdRef.current) {
                conversationIdRef.current = data.conversation_id;
                setConversationId(data.conversation_id);
              } else if (data.type === 'content') {
                // Update the streaming message with new content
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: msg.content + data.text }
                    : msg
                ));
              } else if (data.type === 'complete') {
                // Final update with complete response
                setMessages(prev => {
                  return prev.map(msg =>
                    msg.id === streamingMessageId
                      ? { ...msg, content: data.full_response }
                      : msg
                  );
                });
                if (data.conversation_id && !conversationId) {
                  setConversationId(data.conversation_id);
                }
                setAssistantSpeaking(false);

                // Optionally attach clinical codes for the user's prompt
                if (SHOW_CODES_FOR_CHAT && token) {
                  try {
                    const resp = await apiFetch('/api/clinical/quick-code', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      auth: true,
                      token,
                      body: JSON.stringify({ symptom: content })
                    });
                    if (resp.ok) {
                      const payload = await resp.json().catch(() => null);
                      const raw = payload?.primary_codes as any[];
                      const codes = Array.isArray(raw)
                        ? raw
                            .map((c: any) => ({
                              code: c?.code ?? '',
                              system: c?.system ?? '',
                              display: c?.display ?? '',
                            }))
                            .filter((c) => c.code && c.display)
                        : [];
                      if (codes.length > 0) {
                        setMessages(prev => prev.map(msg =>
                          msg.id === streamingMessageId ? { ...msg, clinicalCodes: codes } : msg
                        ));
                      }
                    }
                  } catch (e) {
                    // Non-fatal; ignore
                  }
                }
              } else if (data.error) {
                throw new Error(data.error);
              }
            } catch (parseError) {
              console.error('Error parsing stream data:', parseError);
            }
          }
        }

        // Check for stall
        if (Date.now() - lastChunkAt > STREAM_TIMEOUT_MS) {
          throw new Error('Stream timed out. Please try again.');
        }
      }
      // Ensure speaking indicator turns off when stream ends
      setAssistantSpeaking(false);
      
    } catch (error: any) {
      console.error('Error sending message:', error);
      toast({ title: 'Chat error', description: error?.message || 'Please try again.', variant: 'destructive' });
      setIsTyping(false);
      setAssistantSpeaking(false);
      
      // Remove any incomplete streaming message and add error
      setMessages(prev => {
        const filtered = prev.filter(msg => msg.content !== "");
        return [...filtered, {
          id: (Date.now() + 2).toString(),
          content: "I apologize, but I'm experiencing technical difficulties. Please try again in a moment. If this is a medical emergency, please call 999 immediately.",
          sender: "doctor",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }];
      });
    } finally {
      setSending(false);
    }
  }, [token, conversationId, currentModel, sending]);

  return (
    <div className="h-screen flex flex-col bg-medical-bg">
      <MedicalHeader />
      <MedicalDisclaimer />


      <div className="flex-1 overflow-y-auto pb-6">
        {/* Speaking avatars indicator */}
        <div className="max-w-4xl mx-auto px-4 mt-2 mb-1 flex items-center justify-between">
          <AvatarBubble initials="DH" label="Dr. Hervix" isSpeaking={assistantSpeaking} colorClass="bg-medical-blue" />
          <AvatarBubble initials="You" label={userSpeaking ? 'Speaking…' : undefined} isSpeaking={userSpeaking} colorClass="bg-gray-500" />
        </div>
        <div className="space-y-1 pt-4">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message.content}
              sender={message.sender}
              timestamp={message.timestamp}
              // Always provide a doctor avatar seed so it consistently renders
              avatar={message.sender === 'doctor' ? (message.avatar ?? DEFAULT_AVATAR) : undefined}
              clinicalCodes={message.clinicalCodes}
            />
          ))}


          {isTyping && (
            <div className="flex gap-3 max-w-4xl mx-auto px-4 mb-6">
              <div className="h-8 w-8 bg-medical-blue rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">DH</span>
              </div>
              <div className="bg-chat-bubble-doctor px-4 py-3 rounded-2xl rounded-tl-md">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-medical-text-muted rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-medical-text-muted rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                  <div className="w-2 h-2 bg-medical-text-muted rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <ChatInput
        onSendMessage={handleSendMessage}
        disabled={isTyping || sending || assistantSpeaking}
        currentModel={currentModel}
        conversationId={conversationId || 'default'}
        onModelSelect={handleModelSelect}
        onVoiceStateChange={({ recording, transcribing }) => setUserSpeaking(recording || transcribing)}
        onVoiceAIResponse={handleVoiceAIResponse}
      />
    </div>
  );
};