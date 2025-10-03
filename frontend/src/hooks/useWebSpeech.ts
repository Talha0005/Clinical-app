import { useCallback, useEffect, useRef, useState } from "react";

type RecognitionType = (window & typeof globalThis) & {
  webkitSpeechRecognition?: any;
  SpeechRecognition?: any;
};

export interface WebSpeechState {
  listening: boolean;
  error: string | null;
  interim: string;
  finalText: string;
  supported: boolean;
}

export interface WebSpeechControls {
  start: () => void;
  stop: () => void;
  reset: () => void;
}

export const useWebSpeech = (): WebSpeechState & WebSpeechControls => {
  const [state, setState] = useState<WebSpeechState>({
    listening: false,
    error: null,
    interim: "",
    finalText: "",
    supported: false,
  });

  const recognitionRef = useRef<any | null>(null);

  useEffect(() => {
    const w = window as RecognitionType;
    const SpeechRec = w.SpeechRecognition || w.webkitSpeechRecognition;
    const supported = Boolean(SpeechRec);
    setState((s) => ({ ...s, supported }));
    if (!SpeechRec) return;

    const rec = new SpeechRec();
    rec.continuous = true;
    rec.interimResults = true;
    try {
      // Prefer en-GB for UK tone; fallback to browser default
      rec.lang = navigator.language || "en-GB";
    } catch {}

    rec.onstart = () => setState((s) => ({ ...s, listening: true, error: null }));
    rec.onend = () => setState((s) => ({ ...s, listening: false }));
    rec.onerror = (e: any) => setState((s) => ({ ...s, error: e?.error || "speech_error" }));
    rec.onresult = (e: any) => {
      let interim = "";
      let finalParts: string[] = [];
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) {
          finalParts.push(res[0].transcript);
        } else {
          interim += res[0].transcript;
        }
      }
      setState((s) => ({
        ...s,
        interim,
        finalText: (s.finalText + " " + finalParts.join(" ")).trim(),
      }));
    };

    recognitionRef.current = rec;
    return () => {
      try { rec.abort(); } catch {}
      recognitionRef.current = null;
    };
  }, []);

  const start = useCallback(() => {
    const rec = recognitionRef.current;
    if (!rec) return;
    try { rec.start(); } catch {}
  }, []);

  const stop = useCallback(() => {
    const rec = recognitionRef.current;
    if (!rec) return;
    try { rec.stop(); } catch {}
  }, []);

  const reset = useCallback(() => {
    setState((s) => ({ ...s, interim: "", finalText: "", error: null }));
  }, []);

  return { ...state, start, stop, reset };
};


