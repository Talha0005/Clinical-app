import { useState, useRef, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';

export interface VoiceRecordingState {
  isRecording: boolean;
  isConnecting: boolean;
  isTranscribing: boolean;
  error: string | null;
  transcription: string;
}

export interface VoiceRecordingControls {
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  clearTranscription: () => void;
}

export const useVoiceRecording = (): VoiceRecordingState & VoiceRecordingControls => {
  const { token } = useAuth();
  const [state, setState] = useState<VoiceRecordingState>({
    isRecording: false,
    isConnecting: false,
    isTranscribing: false,
    error: null,
    transcription: ''
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isConnecting: true, error: null }));

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      streamRef.current = stream;

      // Create WebSocket connection
      const sessionId = `voice_${Date.now()}`;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/api/voice/stream/${sessionId}`;
      
      const ws = new WebSocket(wsUrl);
      websocketRef.current = ws;

      let authenticated = false;

      ws.onopen = () => {
        console.log('🎤 Voice WebSocket connected');
        // Send authentication
        ws.send(JSON.stringify({
          type: 'auth',
          token: token
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'status' && data.status === 'authenticated') {
            authenticated = true;
            setState(prev => ({ 
              ...prev, 
              isConnecting: false, 
              isRecording: true 
            }));
            startAudioRecording();
          } else if (data.type === 'partial_transcript') {
            setState(prev => ({ 
              ...prev, 
              transcription: data.text,
              isTranscribing: true 
            }));
          } else if (data.type === 'final_transcript') {
            setState(prev => ({ 
              ...prev, 
              transcription: data.text,
              isTranscribing: false 
            }));
          } else if (data.type === 'error') {
            setState(prev => ({ 
              ...prev, 
              error: data.error,
              isRecording: false,
              isConnecting: false 
            }));
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('Voice WebSocket error:', error);
        setState(prev => ({ 
          ...prev, 
          error: 'Connection failed',
          isRecording: false,
          isConnecting: false 
        }));
      };

      ws.onclose = () => {
        console.log('🎤 Voice WebSocket closed');
        setState(prev => ({ 
          ...prev, 
          isRecording: false,
          isConnecting: false 
        }));
      };

      const startAudioRecording = () => {
        if (!stream) return;

        const mediaRecorder = new MediaRecorder(stream, {
          mimeType: 'audio/webm;codecs=opus'
        });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN && authenticated) {
            // Convert audio blob to base64 and send
            const reader = new FileReader();
            reader.onload = () => {
              const base64Audio = reader.result?.toString().split(',')[1];
              if (base64Audio) {
                ws.send(JSON.stringify({
                  type: 'audio',
                  data: base64Audio
                }));
              }
            };
            reader.readAsDataURL(event.data);
          }
        };

        mediaRecorder.start(100); // Send chunks every 100ms
      };

    } catch (error) {
      console.error('Error starting voice recording:', error);
      setState(prev => ({ 
        ...prev, 
        error: 'Microphone access denied or not available',
        isRecording: false,
        isConnecting: false 
      }));
    }
  }, [token]);

  const stopRecording = useCallback(() => {
    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Close WebSocket
    if (websocketRef.current) {
      websocketRef.current.send(JSON.stringify({ type: 'close' }));
      websocketRef.current.close();
      websocketRef.current = null;
    }

    setState(prev => ({ 
      ...prev, 
      isRecording: false,
      isConnecting: false,
      isTranscribing: false 
    }));
  }, []);

  const clearTranscription = useCallback(() => {
    setState(prev => ({ ...prev, transcription: '', error: null }));
  }, []);

  return {
    ...state,
    startRecording,
    stopRecording,
    clearTranscription
  };
};