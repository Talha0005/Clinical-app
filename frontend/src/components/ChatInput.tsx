import { useState, useEffect, useRef } from "react";
import { Send, Mic, MicOff, Loader2, Camera, Upload, Settings, ChevronDown, ChevronUp, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useVoiceRecording } from "@/hooks/useVoiceRecording";
import { useImageCapture } from "@/hooks/useImageCapture";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  currentModel?: string;
  conversationId?: string;
  onModelSelect?: (modelId: string) => void;
}

export const ChatInput = ({
  onSendMessage,
  disabled = false,
  currentModel,
  conversationId,
  onModelSelect
}: ChatInputProps) => {
  const [message, setMessage] = useState("");
  const [showModelSelector, setShowModelSelector] = useState(false);
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

  // Update message with transcription and send when done
  useEffect(() => {
    if (transcription) {
      setMessage(transcription);
    }

    if (wasTranscribing.current && !isTranscribing && transcription) {
      onSendMessage(transcription);
      setMessage('');
      clearTranscription();
    }

    wasTranscribing.current = isTranscribing;
  }, [isTranscribing, transcription, onSendMessage, clearTranscription]);

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
            <div className="absolute right-2 bottom-2 flex gap-1">
              {/* Model Selector Button */}
              {currentModel && onModelSelect && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  disabled={disabled}
                  className="h-8 w-8 p-0 hover:bg-secondary"
                  title="AI Model Settings"
                >
                  <Settings className="h-4 w-4 text-medical-text-muted" />
                </Button>
              )}


              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleCameraCapture}
                disabled={disabled || isAnalyzing}
                className={`h-8 w-8 p-0 hover:bg-secondary ${
                  isAnalyzing ? 'bg-green-100 hover:bg-green-200 text-green-600' : ''
                }`}
                title={isAnalyzing ? 'Analyzing image...' : 'Take photo with camera'}
              >
                {isAnalyzing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-medical-blue" />
                ) : (
                  <Camera className="h-4 w-4 text-medical-text-muted" />
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
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={disabled || isAnalyzing}
                  className="h-8 w-8 p-0 hover:bg-secondary"
                  title="Upload image file"
                  asChild
                >
                  <span>
                    <Upload className="h-4 w-4 text-medical-text-muted" />
                  </span>
                </Button>
              </label>

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleVoiceToggle}
                disabled={disabled || isConnecting}
                className={`h-8 w-8 p-0 hover:bg-secondary ${
                  isRecording ? 'bg-red-100 hover:bg-red-200 text-red-600' : 
                  isTranscribing ? 'bg-blue-100 hover:bg-blue-200 text-blue-600' : ''
                }`}
                title={
                  isRecording ? 'Click to stop recording' :
                  isConnecting ? 'Connecting...' :
                  isTranscribing ? 'Transcribing...' :
                  'Click to start voice input'
                }
              >
                {isConnecting || isTranscribing ? (
                  <Loader2 className="h-4 w-4 animate-spin text-medical-blue" />
                ) : isRecording ? (
                  <MicOff className="h-4 w-4" />
                ) : (
                  <Mic className="h-4 w-4 text-medical-text-muted" />
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
                  <Button
                    variant={currentModel === "anthropic/claude-3-opus-20240229" ? "default" : "outline"}
                    className="w-full justify-start h-auto p-4"
                    onClick={() => {
                      onModelSelect("anthropic/claude-3-opus-20240229");
                      setShowModelSelector(false);
                    }}
                  >
                    <div className="text-left">
                      <div className="font-medium">Claude Opus</div>
                      <div className="text-sm opacity-70">Most capable • $0.015/1K tokens • Best for complex diagnosis</div>
                    </div>
                  </Button>

                  <Button
                    variant={currentModel === "anthropic/claude-3-5-sonnet-20241022" ? "default" : "outline"}
                    className="w-full justify-start h-auto p-4"
                    onClick={() => {
                      onModelSelect("anthropic/claude-3-5-sonnet-20241022");
                      setShowModelSelector(false);
                    }}
                  >
                    <div className="text-left">
                      <div className="font-medium">Claude Sonnet</div>
                      <div className="text-sm opacity-70">Balanced • $0.003/1K tokens • Great for general consultation</div>
                    </div>
                  </Button>

                  <Button
                    variant={currentModel === "ollama/medllama2" ? "default" : "outline"}
                    className="w-full justify-start h-auto p-4"
                    onClick={() => {
                      onModelSelect("ollama/medllama2");
                      setShowModelSelector(false);
                    }}
                  >
                    <div className="text-left">
                      <div className="font-medium">Medical Llama</div>
                      <div className="text-sm opacity-70">Private & Free • Local model • Medical specialist</div>
                    </div>
                  </Button>
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