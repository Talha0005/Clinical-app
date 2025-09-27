import { useState, useEffect, useRef } from "react";
import { Send, Mic, MicOff, Loader2, Camera, Upload, Settings, ChevronDown, ChevronUp, Brain } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useVoiceRecording } from "@/hooks/useVoiceRecording";
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
}

export const ChatInput = ({
  onSendMessage,
  disabled = false,
  currentModel,
  conversationId,
  onModelSelect,
  onVoiceStateChange
}: ChatInputProps) => {
  const [message, setMessage] = useState("");
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [availableModels, setAvailableModels] = useState<Array<{ id: string; name: string }>>([]);
  const [isAssessing, setIsAssessing] = useState(false);
  const { token } = useAuth();
  const {
    isRecording,
    isConnecting,
    isTranscribing,
    error,
    transcription,
    startRecording,
    stopRecording,
    clearTranscription
  } = useVoiceRecording();

  const {
    isAnalyzing,
    error: imageError,
    result: imageResult,
    captureFromCamera,
    uploadFile,
    clearResult
  } = useImageCapture();

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

  // Notify parent about voice state updates (for avatar speaking indicator)
  useEffect(() => {
    if (typeof onVoiceStateChange === 'function') {
      onVoiceStateChange({ recording: isRecording, transcribing: isTranscribing });
    }
  }, [isRecording, isTranscribing, onVoiceStateChange]);

  // Update message with image analysis result
  useEffect(() => {
    if (imageResult) {
      const analysisText = `Medical Image Analysis:
Findings: ${imageResult.findings.join(', ')}
Severity: ${imageResult.severity}
Recommendations: ${imageResult.recommendations.join(', ')}`;
      setMessage(analysisText);
    }
  }, [imageResult]);

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
    if (isRecording) {
      stopRecording();
    } else {
      clearTranscription();
      await startRecording();
    }
  };

  const handleCameraCapture = async () => {
    clearResult();
    await captureFromCamera();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      clearResult();
      uploadFile(file);
    }
  };

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

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
                  variant="ghost"
                  type="button"
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  disabled={disabled}
                  className={cn(
                    "h-8 w-8 p-0 bg-gray-200 hover:bg-gray-300 border border-gray-300 "
                  )}
                  title="AI Model Settings"
                >
                  <Settings className="h-4 w-4 text-gray-700" />
                </Button>
              )}

              {/* Clinical Assessment Button */}
              <Button
                variant="ghost"
                type="button"
                onClick={handleClinicalAssessment}
                disabled={disabled || isAssessing}
                className={cn(
                  "h-8 w-8 p-0 bg-gray-200 hover:bg-gray-300 border border-gray-300",
                  isAssessing ? "ring-2 ring-blue-300" : ""
                )}
                title={isAssessing ? 'Assessing...' : 'Run Clinical Assessment'}
              >
                {isAssessing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                ) : (
                  <Brain className="h-4 w-4 text-gray-700" />
                )}
              </Button>


              <Button
                variant="ghost"
                type="button"
                onClick={handleCameraCapture}
                disabled={disabled || isAnalyzing}
                className={cn(
                  "h-8 w-8 p-0 bg-gray-200 hover:bg-gray-300 border border-gray-300",
                  isAnalyzing ? "ring-2 ring-green-300" : ""
                )}
                title={isAnalyzing ? 'Analyzing image...' : 'Take photo with camera'}
              >
                {isAnalyzing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
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
                  variant="ghost"
                  type="button"
                  disabled={disabled || isAnalyzing}
                  className={cn(
                    "h-8 w-8 p-0 bg-gray-200 hover:bg-gray-300 border border-gray-300"
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
                variant="ghost"
                type="button"
                onClick={handleVoiceToggle}
                disabled={disabled || isConnecting}
                className={cn(
                  "h-8 w-8 p-0 bg-gray-200 hover:bg-gray-300 border border-gray-300",
                  isRecording
                    ? "ring-2 ring-red-300"
                    : isTranscribing
                      ? "ring-2 ring-blue-300"
                      : ""
                )}
                title={
                  isRecording ? 'Click to stop recording' :
                  isConnecting ? 'Connecting...' :
                  isTranscribing ? 'Transcribing...' :
                  'Click to start voice input'
                }
              >
                {isConnecting || isTranscribing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                ) : isRecording ? (
                  <MicOff className="h-4 w-4" />
                ) : (
                  <Mic className="h-4 w-4 text-gray-700" />
                )}
              </Button>
            </div>
          </div>
          
          <Button
            type="submit"
            disabled={!message.trim() || disabled}
            className="bg-medical-blue hover:bg-medical-blue-dark text-white h-[52px] px-6"
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
                  <Brain className="w-5 h-5 text-primary" />
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
                          ? "bg-medical-blue text-white hover:bg-medical-blue-dark"
                          : "bg-white border border-border text-black hover:bg-medical-blue hover:text-white"
                      )}
                      title={currentModel === m.id ? 'Current model' : `Switch to ${m.name}`}
                      onClick={() => {
                        if (isActive) return; // no-op if already current
                        onModelSelect?.(m.id);
                        setShowModelSelector(false);
                      }}
                    >
                      <div className="text-left">
                        <div className={cn("font-medium", isActive ? "text-white" : "text-black group-hover:text-white")}>{m.name}</div>
                        <div className={cn("text-sm", isActive ? "text-blue-50" : "text-gray-600 group-hover:text-blue-50") }>
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
    </div>
  );
};