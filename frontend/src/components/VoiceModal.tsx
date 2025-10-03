import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface VoiceModalProps {
  open: boolean;
  onClose: () => void;
  listening: boolean;
  interim: string;
  finalText: string;
}

export const VoiceModal: React.FC<VoiceModalProps> = ({ open, onClose, listening, interim, finalText }) => {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 animate-fade-in" onClick={onClose} />
      <div className={cn(
        "relative bg-white w-full max-w-md mx-4 rounded-2xl shadow-2xl p-6",
        "animate-scale-in"
      )}>
        <button aria-label="Close" onClick={onClose} className="absolute top-3 right-3 rounded-full p-1 hover:bg-gray-100">
          <X className="h-5 w-5" />
        </button>

        <div className="flex flex-col items-center text-center">
          <div className="relative h-24 w-24">
            <div className="absolute inset-0 rounded-full bg-blue-500" />
            {listening && (
              <div className="absolute inset-[-8px] rounded-full bg-blue-500/20 animate-ping" />
            )}
            <div className="absolute inset-2 rounded-full bg-white flex items-center justify-center text-blue-600 font-semibold">
              DH
            </div>
          </div>
          <div className="mt-4 text-gray-700 text-sm">
            {listening ? "Listening… speak naturally" : "Starting microphone…"}
          </div>
          <div className="mt-3 w-full text-left">
            <div className="text-xs text-gray-500">Interim</div>
            <div className="min-h-[40px] text-sm text-gray-800 border rounded-md p-2 bg-gray-50">
              {interim || "…"}
            </div>
          </div>
          <div className="mt-3 w-full text-left">
            <div className="text-xs text-gray-500">Final</div>
            <div className="min-h-[48px] text-sm text-gray-800 border rounded-md p-2">
              {finalText || ""}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .animate-fade-in{animation:fade-in .2s ease-out both}
        @keyframes fade-in{from{opacity:0}to{opacity:1}}
        .animate-scale-in{animation:scale-in .18s ease-out both}
        @keyframes scale-in{from{opacity:.6;transform:scale(.96)}to{opacity:1;transform:scale(1)}}
      `}</style>
    </div>
  );
};

export default VoiceModal;


