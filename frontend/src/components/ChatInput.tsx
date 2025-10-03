import { useState, useEffect, useRef } from "react";
import { Send, Mic, MicOff, Loader2, Camera, Upload, Settings, ChevronDown, ChevronUp, Brain } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useVoiceRecording } from "@/hooks/useVoiceRecording";
import { useWebSpeech } from "@/hooks/useWebSpeech";
import VoiceModal from "./VoiceModal";
import { useImageCapture } from "@/hooks/useImageCapture";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, apiFetchJson } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  currentModel?: string;
  conversationId?: string;
  onModelSelect?: (modelId: string) => void;
  onVoiceStateChange?: (state: { recording: boolean; transcribing: boolean }) => void;
  onVoiceAIResponse?: (response: string, meta?: any) => void;
}

export const ChatInput = ({
  onSendMessage,
  disabled = false,
  currentModel,
  conversationId,
  onModelSelect,
  onVoiceStateChange,
  onVoiceAIResponse
}: ChatInputProps) => {
  const [message, setMessage] = useState("");
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [availableModels, setAvailableModels] = useState<Array<{ id: string; name: string }>>([]);
  const [isAssessing, setIsAssessing] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  // Removed multi-image state - back to single image handling
  const { token } = useAuth();
  const {
    isRecording,
    isConnecting,
    isTranscribing,
    error,
    transcription,
    llmResponse,
    llmMeta,
    isGeneratingResponse,
    startRecording,
    stopRecording,
    clearTranscription,
    clearLlmResponse
  } = useVoiceRecording();

  // Web Speech recognition for lightweight local transcription UX
  const { listening, start, stop, reset, interim, finalText, supported } = useWebSpeech();

  const {
    isAnalyzing,
    error: imageError,
    result: imageResult,
    captureFromCamera,
    uploadFile,
    analyzeImage,
    clearResult
  } = useImageCapture();

  // Debug: Log when imageResult changes
  useEffect(() => {
    if (imageResult) {
      console.log('🔍 imageResult changed:', imageResult);
    }
  }, [imageResult]);

  // Prevent duplicate auto-sends for the same image analysis
  const lastImageSigRef = useRef<string | null>(null);
  // Guard against rapid duplicate sends (double onChange, re-renders, etc.)
  const imageSendInFlightRef = useRef<boolean>(false);
  const lastImageSendAtRef = useRef<number>(0);

  const wasTranscribing = useRef(isTranscribing);

  // Update message with transcription and auto-send when final transcript arrives
  useEffect(() => {
    if (transcription) {
      setMessage(transcription);
    }

    // Auto-send when transcription just finished
    if (wasTranscribing.current && !isTranscribing && transcription) {
      onSendMessage(transcription.trim());
      setMessage("");
      clearTranscription();
    }

    wasTranscribing.current = isTranscribing;
  }, [isTranscribing, transcription, onSendMessage, clearTranscription]);

  // Handle LLM response from voice - pass to parent for AI response display
  useEffect(() => {
    if (llmResponse && onVoiceAIResponse) {
      console.log('🎤 Passing voice response to parent:', llmResponse);
      // Pass the LLM response to parent component for proper AI message display
      onVoiceAIResponse(llmResponse, llmMeta);
      // Clear the LLM response after passing to parent
      setTimeout(() => clearLlmResponse(), 500);
    }
  }, [llmResponse, llmMeta, onVoiceAIResponse, clearLlmResponse]);

  // Notify parent about voice state updates (for avatar speaking indicator)
  useEffect(() => {
    if (typeof onVoiceStateChange === 'function') {
      onVoiceStateChange({ recording: isRecording, transcribing: isTranscribing });
    }
  }, [isRecording, isTranscribing, onVoiceStateChange]);

  // Helper: stable stringify to generate a consistent signature
  const stableStringify = (value: any): string => {
    const sorter = (val: any): any => {
      if (Array.isArray(val)) return val.map(sorter);
      if (val && typeof val === 'object') {
        return Object.keys(val)
          .sort()
          .reduce((acc: any, k) => {
            acc[k] = sorter(val[k]);
            return acc;
          }, {});
      }
      return val;
    };
    try {
      return JSON.stringify(sorter(value));
    } catch {
      return String(Date.now());
    }
  };

  // Re-enabled: Auto-send image analysis for single image
  useEffect(() => {
    if (!imageResult) return;
    
    console.log('🔄 Auto-sending image analysis result');
    
    // Format the image analysis result as a readable message
    const message = `📷 **Medical Image Analysis Results**

**Findings:**
${imageResult.findings.map(f => `• ${f}`).join('\n')}

**Risk Assessment:** ${imageResult.severity}

**Recommendations:**
${imageResult.recommendations.map(r => `• ${r}`).join('\n')}

${imageResult.clinical_coding ? `**Clinical Codes:** ${imageResult.clinical_coding.snomed_codes.map(c => `${c.display} (${c.code})`).join(', ')}` : ''}

*This analysis is for informational purposes only. Please consult with a healthcare professional for proper medical evaluation.*`;
    
    onSendMessage(message);
    clearResult();
  }, [imageResult, onSendMessage, clearResult]);

  // Load available models from backend (filters out unsupported options on this environment)
  useEffect(() => {
    const loadModels = async () => {
      if (!token) return;
      try {
        const resp = await apiFetch('/api/models/available', { auth: true, token });
        if (!resp.ok) return;
        const data = await resp.json();
        const models = Array.isArray(data?.models) ? data.models : [];
        setAvailableModels(models.map((m: any) => ({ id: m.id, name: m.name })));
      } catch (e) {
        // Non-fatal; keep hardcoded fallback buttons if needed
        console.warn('Failed to load available models', e);
      }
    };
    loadModels();
  }, [token]);

  const handleVoiceToggle = async () => {
    // Open modal and start web-speech listening
    setShowVoiceModal(true);
    reset();
    if (supported) start();
  };

  const handleCameraCapture = async () => {
    try {
      console.log('📷 Camera capture triggered');
      const file = await captureFromCamera();
      if (file) {
        console.log('📷 Camera capture successful:', file.name, file.type, file.size);
        // Auto-analyze single image like before
        await analyzeImage(file);
      }
    } catch (error) {
      console.error('Camera capture failed:', error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('📁 File upload triggered');
    const files = Array.from(e.target.files || []);
    console.log('📁 Files selected:', files.length);
    
    if (files.length > 0) {
      // Take only the first file for single image handling
      const file = files[0];
      console.log('📁 Processing single file:', file.name, file.type, file.size);
      
      if (file.type.startsWith('image/') && file.size <= 10 * 1024 * 1024) {
        // Auto-analyze single image like before
        await analyzeImage(file);
      } else {
        toast({
          title: 'Invalid file',
          description: `${file.name} is not a valid image or is too large (max 10MB)`,
          variant: 'destructive'
        });
      }
      
      // Clear the input
      e.target.value = '';
    }
  };

  // Removed multi-image functions - back to single image handling

  const handleClinicalAssessment = async () => {
    if (!message.trim()) {
      toast({ title: 'Enter symptoms first', description: 'Please describe the patient message before running a clinical assessment.' });
      return;
    }
    try {
      setIsAssessing(true);
      const res = await apiFetchJson<any>("/api/medical/clinical/comprehensive-assessment", {
        method: "POST",
        auth: true,
        token,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_message: message.trim() })
      });

      if (!res || res.success === false) {
        throw new Error(res?.error || 'Assessment failed');
      }

      const assessment = res.assessment ?? res;
      const summary = typeof assessment === 'string' ? assessment : JSON.stringify(assessment, null, 2);
      setMessage(`Clinical Assessment:\n${summary}`);
      toast({ title: 'Clinical assessment ready', description: 'Review and send to include in the conversation.' });
    } catch (err: any) {
      console.error('Clinical assessment error:', err);
      toast({ title: 'Clinical assessment failed', description: err?.message || 'Please try again.', variant: 'destructive' });
    } finally {
      setIsAssessing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  // Removed sendMessageWithImages - back to single image handling

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
        <div className="bg-medical-surface border-t border-border">
          <div className="max-w-4xl mx-auto p-4">
            <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe your symptoms or ask a medical question..."
              className="min-h-[52px] max-h-32 resize-none bg-chat-input-bg border-border focus:border-medical-blue pr-32"
              disabled={disabled}
            />
            {/* Model Selector, Camera, Upload, and Voice buttons */}
            <div className="absolute right-2 bottom-2 flex gap-1 ">
              {/* Model Selector Button */}
              {currentModel && onModelSelect && (
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  disabled={disabled}
                  className={cn(
                    "h-8 w-8 p-0 bg-gray-100 hover:bg-gray-200 border-2 border-gray-300 shadow-lg"
                  )}
                  title="AI Model Settings"
                >
                  <Settings className="h-4 w-4 text-gray-700" />
                </Button>
              )}

              {/* Clinical Assessment Button */}
              <Button
                variant="outline"
                type="button"
                onClick={handleClinicalAssessment}
                disabled={disabled || isAssessing}
                className={cn(
                  "h-8 w-8 p-0 bg-gray-100 hover:bg-gray-200 border-2 border-gray-300 shadow-lg",
                  isAssessing ? "ring-2 ring-green-400" : ""
                )}
                title={isAssessing ? 'Assessing...' : 'Run Clinical Assessment'}
              >
                {isAssessing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-green-400" />
                ) : (
                  <Brain className="h-4 w-4 text-gray-700" />
                )}
              </Button>


              <Button
                variant="outline"
                type="button"
                onClick={handleCameraCapture}
                disabled={disabled || isAnalyzing}
                className={cn(
                  "h-8 w-8 p-0 bg-gray-100 hover:bg-gray-200 border-2 border-gray-300 shadow-lg",
                  isAnalyzing ? "ring-2 ring-green-400" : ""
                )}
                title={isAnalyzing ? 'Analyzing image...' : 'Take photo with camera'}
              >
                {isAnalyzing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-green-400" />
                ) : (
                  <Camera className="h-4 w-4 text-gray-700" />
                )}
              </Button>
              
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={disabled || isAnalyzing}
                />
                <Button
                  variant="outline"
                  type="button"
                  disabled={disabled || isAnalyzing}
                  className={cn(
                    "h-8 w-8 p-0 bg-gray-100 hover:bg-gray-200 border-2 border-gray-300 shadow-lg"
                  )}
                  title="Upload image file"
                  asChild
                >
                  <span>
                    <Upload className="h-4 w-4 text-gray-700" />
                  </span>
                </Button>
              </label>

              <Button
                variant="outline"
                type="button"
                onClick={handleVoiceToggle}
                disabled={disabled || isConnecting}
                className={cn(
                  "h-8 w-8 p-0 bg-gray-100 hover:bg-gray-200 border-2 border-gray-300 shadow-lg",
                  isRecording
                    ? "ring-2 ring-red-400 bg-red-100 hover:bg-red-200"
                    : isTranscribing
                      ? "ring-2 ring-blue-400 bg-blue-100 hover:bg-blue-200"
                      : isGeneratingResponse
                        ? "ring-2 ring-green-400 bg-green-100 hover:bg-green-200"
                        : ""
                )}
                title={
                  isRecording ? 'Click to stop recording' :
                  isConnecting ? 'Connecting...' :
                  isTranscribing ? 'Transcribing...' :
                  isGeneratingResponse ? 'AI is responding...' :
                  'Click to start voice input'
                }
              >
                {isConnecting || isTranscribing || isGeneratingResponse ? (
                  <Loader2 className="h-4 w-4 animate-spin text-gray-700" />
                ) : isRecording ? (
                  <MicOff className="h-4 w-4 text-gray-700" />
                ) : (
                  <Mic className="h-4 w-4 text-gray-700" />
                )}
              </Button>
            </div>
          </div>
          
          <Button
            type="submit"
            disabled={!message.trim() || disabled}
            className="bg-gray-100 hover:bg-gray-200 text-gray-700 border-2 border-gray-300 shadow-lg h-[52px] px-6"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>

        {/* Simplified Model Selector */}
        {showModelSelector && currentModel && onModelSelect && (
          <div className="mt-4">
            <Card className="w-full">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Brain className="w-5 h-5 text-black" />
                  Select AI Model
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid gap-3">
                  {(availableModels.length > 0
                    ? availableModels
                    : [
                        // Fallback to only the known-supported default model when API list isn't available
                        { id: 'anthropic/claude-3-5-sonnet-20240620', name: 'Claude Sonnet' },
                      ]
                  ).map((m) => {
                    const isActive = currentModel === m.id;
                    return (
                    <Button
                      key={m.id}
                      className={cn(
                        "w-full justify-between h-auto p-4 text-left group transition-colors",
                        isActive
                          ? "bg-white text-gray-800 border-2 border-gray-400 shadow-md"
                          : "bg-white border border-gray-300 text-gray-700 hover:bg-blue-600 hover:text-white"
                      )}
                      title={currentModel === m.id ? 'Current model' : `Switch to ${m.name}`}
                      onClick={() => {
                        if (isActive) return; // no-op if already current
                        onModelSelect?.(m.id);
                        setShowModelSelector(false);
                      }}
                    >
                      <div className="text-left">
                        <div className={cn("font-medium", isActive ? "text-gray-800" : "text-gray-700 group-hover:text-white")}>{m.name}</div>
                        <div className={cn("text-sm", isActive ? "text-gray-600" : "text-gray-500 group-hover:text-white") }>
                          {m.id.includes('opus') && 'Most capable • Best for complex diagnosis'}
                          {m.id.includes('sonnet') && 'Balanced • Great for general consultation'}
                          {m.id.includes('gpt-4o') && 'OpenAI • Multimodal • Vision capable'}
                          {m.id.includes('gemini') && 'Google • Long context • Vision capable'}
                        </div>
                      </div>
                      {isActive && (
                        <span className="ml-3 text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">Current</span>
                      )}
                    </Button>
                  )})}
                </div>
              </CardContent>
            </Card>
          </div>
        )}


        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm mt-2">
            <strong>Voice Error:</strong> {error}
          </div>
        )}
        
        {imageError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm mt-2">
            <strong>Image Error:</strong> {imageError}
          </div>
        )}
        
        <p className="text-xs text-medical-text-muted text-center mt-3">
          Dr. Hervix is here to help with your medical concerns. Press Enter to send, Shift+Enter for new line.
          {!disabled && ' Use the camera 📷 for medical images, upload 📎 for files, or mic 🎤 for voice input.'}
        </p>
      </div>
      
        <VoiceModal
          open={showVoiceModal}
          onClose={() => {
            stop();
            setShowVoiceModal(false);
            const text = (finalText || interim || "").trim();
            if (text) {
              onSendMessage(text);
              setMessage("");
            }
          }}
          listening={listening}
          interim={interim}
          finalText={finalText}
        />
      </div>
  );
};