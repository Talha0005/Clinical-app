import { useState, useRef, useCallback } from "react";
import { MedicalHeader } from "./MedicalHeader";
import { MedicalDisclaimer } from "./MedicalDisclaimer";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { useAuth } from "../hooks/useAuth";

interface Message {
  id: string;
  content: string;
  sender: "doctor" | "user";
  timestamp: string;
}

export const DigiClinic = () => {
  const { token } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Good afternoon! I'm Dr. Hervix, your digital GP consultant. I'm here to help you with any medical concerns you may have. Before we begin, please note that this is a consultation tool to help assess your symptoms and provide guidance. For emergencies, please call 999 immediately. How can I help you today?",
      sender: "doctor",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const conversationIdRef = useRef<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  // Model selection state
  const [currentModel, setCurrentModel] = useState<string>("claude-3-5-sonnet-20241022");

  // Handle model selection
  const handleModelSelect = async (modelId: string) => {
    try {
      // Switch to the new model via API
      const response = await fetch('/api/models/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          model_id: modelId,
          conversation_id: conversationId || 'default',
          reason: 'User requested model switch'
        })
      });

      const result = await response.json();
      if (result.success) {
        setCurrentModel(modelId);

        // Add a system message to show the model switch
        const switchMessage: Message = {
          id: Date.now().toString(),
          content: `🔄 Switched to ${result.message || modelId}. How can I continue to help you?`,
          sender: "doctor",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, switchMessage]);
      }
    } catch (error) {
      console.error('Failed to switch model:', error);
    }
  };


  const handleSendMessage = async (content: string) => {
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
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      
      setMessages(prev => [...prev, streamingMessage]);
      setIsTyping(false);

      // Use the model selection API with streaming
      const response = await fetch('/api/models/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
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
                setMessages(prev => prev.map(msg => 
                  msg.id === streamingMessageId 
                    ? { ...msg, content: data.full_response }
                    : msg
                ));
                if (data.conversation_id && !conversationId) {
                  setConversationId(data.conversation_id);
                }
              } else if (data.error) {
                throw new Error(data.error);
              }
            } catch (parseError) {
              console.error('Error parsing stream data:', parseError);
            }
          }
        }
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
      setIsTyping(false);
      
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
    }
  };

  return (
    <div className="h-screen flex flex-col bg-medical-bg">
      <MedicalHeader />
      <MedicalDisclaimer />


      <div className="flex-1 overflow-y-auto pb-6">
        <div className="space-y-1 pt-4">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message.content}
              sender={message.sender}
              timestamp={message.timestamp}
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
        disabled={isTyping}
        currentModel={currentModel}
        conversationId={conversationId || 'default'}
        onModelSelect={handleModelSelect}
      />
    </div>
  );
};