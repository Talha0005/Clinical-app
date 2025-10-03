import React from 'react';

interface AvatarBubbleProps {
  initials: string;
  label?: string;
  isSpeaking?: boolean;
  colorClass?: string; // e.g., 'bg-medical-blue'
}

export const AvatarBubble: React.FC<AvatarBubbleProps> = ({
  initials,
  label,
  isSpeaking = false,
  colorClass = 'bg-medical-blue',
}) => {
  return (
    <div className="flex items-center gap-2 select-none">
      <div className="relative">
        <div className={`h-9 w-9 ${colorClass} rounded-full flex items-center justify-center text-white text-sm font-semibold`}>{initials}</div>
        {isSpeaking && (
          <div className="absolute inset-0 rounded-full animate-ping bg-blue-400 opacity-30" />
        )}
      </div>
      {label && (
        <div className="text-xs text-medical-text-muted">
          {label}
        </div>
      )}
    </div>
  );
};

export default AvatarBubble;
