import { useState, useRef, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { toast } from '@/hooks/use-toast';

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
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const connectTimeoutRef = useRef<number | null>(null);
  const pendingCloseRef = useRef<number | null>(null);
  const awaitingCompletedRef = useRef<boolean>(false);

  const startRecording = useCallback(async () => {
    try {
      if (!token) {
        toast({ title: 'Login required', description: 'Please log in to use voice input.', variant: 'destructive' });
        throw new Error('Not authenticated');
      }
      setState(prev => ({ ...prev, isConnecting: true, error: null }));

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          // Explicitly request 16 kHz if browser supports it
          sampleRate: 16000 as any,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      // Create WebSocket connection
      const sessionId = `voice_${Date.now()}`;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/api/voice/stream/${sessionId}`;
      
      let attempts = 0;
      const maxAttempts = 3;

      const connect = () => {
        attempts += 1;
        const ws = new WebSocket(wsUrl);
        websocketRef.current = ws;

      let authenticated = false;

        // Safety timeout: if auth doesn't complete within 8s, reset gracefully
        if (connectTimeoutRef.current) {
          window.clearTimeout(connectTimeoutRef.current);
          connectTimeoutRef.current = null;
        }
        connectTimeoutRef.current = window.setTimeout(() => {
          if (!authenticated) {
            try {
              ws.close();
            } catch {}
            setState(prev => ({
              ...prev,
              isRecording: false,
              isConnecting: false,
              error: 'Voice service is not responding. Please try again.'
            }));
            toast({
              title: 'Voice timeout',
              description: 'Connection took too long. Please try again.',
              variant: 'destructive',
            });
          }
        }, 8000);

        ws.onopen = () => {
          console.log('🎤 Voice WebSocket connected');
          toast({ title: 'Voice', description: 'Connected. Authenticating…' });
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
            if (connectTimeoutRef.current) {
              window.clearTimeout(connectTimeoutRef.current);
              connectTimeoutRef.current = null;
            }
            setState(prev => ({ 
              ...prev, 
              isConnecting: false, 
              isRecording: true 
            }));
            toast({ title: 'Listening', description: 'Start speaking… 🎙️' });
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
            // Do NOT close immediately here; wait for server 'completed'
          } else if (data.type === 'status') {
            // Show human-friendly status messages
            if (data.status === 'no_api_key') {
              toast({ title: 'Voice disabled', description: 'Server missing ASSEMBLYAI_API_KEY.', variant: 'destructive' });
              setState(prev => ({ ...prev, isRecording: false, isConnecting: false }));
            } else if (data.status === 'completed') {
              // Server indicates processing complete; close socket now
              try { websocketRef.current?.close(); } catch {}
              if (pendingCloseRef.current) {
                window.clearTimeout(pendingCloseRef.current);
                pendingCloseRef.current = null;
              }
              awaitingCompletedRef.current = false;
              toast({ title: 'Voice', description: 'Transcription completed.' });
            }
          } else if (data.type === 'error') {
            setState(prev => ({ 
              ...prev, 
              error: data.error,
              isRecording: false,
              isConnecting: false 
            }));
            toast({ title: 'Voice error', description: String(data.error), variant: 'destructive' });
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

        ws.onerror = (error) => {
          console.error('Voice WebSocket error:', error);
          toast({ title: 'Voice connection error', description: 'Reconnecting...', variant: 'destructive' });
          setState(prev => ({ 
            ...prev, 
            error: 'Connection failed',
            isRecording: false,
            isConnecting: false 
          }));
        };

        ws.onclose = () => {
          console.log('🎤 Voice WebSocket closed');
          if (connectTimeoutRef.current) {
            window.clearTimeout(connectTimeoutRef.current);
            connectTimeoutRef.current = null;
          }
          if (state.isRecording && attempts < maxAttempts) {
            const backoff = Math.min(1000 * attempts, 3000);
            setTimeout(connect, backoff);
            return;
          }
          setState(prev => ({ 
            ...prev, 
            isRecording: false,
            isConnecting: false 
          }));
        };

      const startAudioRecording = () => {
        if (!stream) return;

        // Use Web Audio API to capture PCM and downsample to 16k mono PCM16
        const AudioContextCtor: typeof AudioContext = (window as any).AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContextCtor({ sampleRate: 48000 });
        audioContextRef.current = audioContext;

        const sourceNode = audioContext.createMediaStreamSource(stream);
        sourceNodeRef.current = sourceNode;

        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN || !authenticated) return;

          const input = e.inputBuffer.getChannelData(0);

          // Downsample from audioContext.sampleRate (likely 48k) to 16k
          const targetRate = 16000;
          const sourceRate = audioContext.sampleRate;
          const sampleRateRatio = sourceRate / targetRate;
          const newLength = Math.round(input.length / sampleRateRatio);
          const downsampled = new Float32Array(newLength);
          let offsetResult = 0;
          let offsetBuffer = 0;
          while (offsetResult < downsampled.length) {
            const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
            // Simple averaging for downsampling
            let accum = 0, count = 0;
            for (let i = offsetBuffer; i < nextOffsetBuffer && i < input.length; i++) {
              accum += input[i];
              count++;
            }
            downsampled[offsetResult] = accum / count;
            offsetResult++;
            offsetBuffer = nextOffsetBuffer;
          }

          // Convert Float32 [-1,1] to PCM16 LE
          const buffer = new ArrayBuffer(downsampled.length * 2);
          const view = new DataView(buffer);
          let offset = 0;
          for (let i = 0; i < downsampled.length; i++, offset += 2) {
            let s = Math.max(-1, Math.min(1, downsampled[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
          }

          // Base64 encode
          const bytes = new Uint8Array(buffer);
          let binary = '';
          for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
          const base64Audio = btoa(binary);

          ws.send(JSON.stringify({ type: 'audio', data: base64Audio }));
        };

        sourceNode.connect(processor);
        processor.connect(audioContext.destination);
      };

      };

      connect();

    } catch (error) {
      console.error('Error starting voice recording:', error);
      setState(prev => ({ 
        ...prev, 
        error: 'Microphone access denied or not available',
        isRecording: false,
        isConnecting: false 
      }));
      toast({ title: 'Voice error', description: 'Microphone access denied or not available.', variant: 'destructive' });
    }
  }, [token]);

  const stopRecording = useCallback(() => {
    // Clear any pending connect timeout
    if (connectTimeoutRef.current) {
      window.clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }
    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Close WebSocket
    if (websocketRef.current) {
      try {
        awaitingCompletedRef.current = true;
        websocketRef.current.send(JSON.stringify({ type: 'close' }));
      } catch {}
      // Allow time for server to flush and send final transcript/response.
      // Prefer waiting for 'completed' status, but set a fallback.
      if (pendingCloseRef.current) {
        window.clearTimeout(pendingCloseRef.current);
        pendingCloseRef.current = null;
      }
      pendingCloseRef.current = window.setTimeout(() => {
        if (awaitingCompletedRef.current) {
          try { websocketRef.current?.close(); } catch {}
          awaitingCompletedRef.current = false;
        }
        websocketRef.current = null;
        if (pendingCloseRef.current) {
          window.clearTimeout(pendingCloseRef.current);
          pendingCloseRef.current = null;
        }
      }, 3000);
    }

    // Disconnect audio nodes
    try {
      processorRef.current?.disconnect();
    } catch {}
    try {
      sourceNodeRef.current?.disconnect();
    } catch {}
    try {
      audioContextRef.current?.close();
    } catch {}
    processorRef.current = null;
    sourceNodeRef.current = null;
    audioContextRef.current = null;

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