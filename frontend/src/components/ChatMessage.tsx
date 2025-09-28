import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface ChatMessageProps {
  message: string;
  sender: "doctor" | "user";
  timestamp?: string;
  avatar?: string;
  clinicalCodes?: Array<{ code: string; system: string; display: string }>;
  showAgentProgress?: boolean;
  agentProgress?: Array<{
    id: string;
    name: string;
    status: 'pending' | 'active' | 'completed' | 'error';
    icon: React.ReactNode;
    description: string;
  }>;
  currentAgent?: string;
}

export const ChatMessage = ({ message, sender, timestamp, avatar, clinicalCodes, showAgentProgress, agentProgress, currentAgent }: ChatMessageProps) => {
  const isDoctor = sender === "doctor";

  // Create a deterministic inline SVG avatar so it always renders.
  const makeAvatarSvg = (seed?: string, size = 32) => {
    const base = (seed || "dr_hervix").toLowerCase();
    const words = base.replace(/[_-]+/g, " ").split(/\s+/).filter(Boolean);
    const initials = (words[0]?.[0] || "D").toUpperCase() + (words[1]?.[0] || "H").toUpperCase();
    // Simple hash to pick a background color from a small palette
    let h = 0;
    for (let i = 0; i < base.length; i++) h = (h * 31 + base.charCodeAt(i)) >>> 0;
    const palette = ["#1d4ed8", "#0ea5e9", "#2563eb", "#0891b2", "#7c3aed", "#0ea5e9"];
    const bg = palette[h % palette.length];
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${size}' height='${size}'>
      <rect width='${size}' height='${size}' rx='${size/2}' fill='${bg}'/>
      <text x='${size/2}' y='${Math.floor(size*0.66)}' text-anchor='middle' font-family='Arial,Segoe UI,Ubuntu' font-weight='600' font-size='${Math.floor(size*0.4)}' fill='#ffffff'>${initials}</text>
    </svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  };

  // Doctor-specific avatar (simple professional silhouette) as inline SVG
  const makeDoctorAvatarSvg = (size = 32) => {
    const svg = `
    <svg xmlns='http://www.w3.org/2000/svg' width='${size}' height='${size}' viewBox='0 0 64 64'>
      <defs>
        <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0%' stop-color='#4f46e5'/>
          <stop offset='100%' stop-color='#06b6d4'/>
        </linearGradient>
      </defs>
      <rect width='64' height='64' rx='32' fill='url(#g)'/>
      <!-- head -->
      <circle cx='32' cy='22' r='10' fill='#f8fafc'/>
      <!-- body/coat -->
      <path d='M16 48c0-8.8 7.2-16 16-16s16 7.2 16 16v6H16v-6z' fill='#e2e8f0'/>
      <!-- stethoscope -->
      <path d='M24 32c0 6 4 10 8 10s8-4 8-10' fill='none' stroke='#0ea5e9' stroke-width='2' stroke-linecap='round'/>
      <circle cx='42' cy='30' r='3' fill='none' stroke='#0ea5e9' stroke-width='2'/>
    </svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  };

  // If avatar is a URL (http/https) or data URI or root-relative path, use it.
  // Otherwise: for doctor, render the doctor icon; for user, render seeded initials.
  const isUrlLike = (v?: string) => !!v && (/^https?:\/\//i.test(v) || v.startsWith("data:") || v.startsWith("/"));
  const avatarSrc = isUrlLike(avatar)
    ? (avatar as string)
    : (isDoctor ? makeDoctorAvatarSvg() : makeAvatarSvg(avatar));
  const fallbackSvg = encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'>
      <rect width='32' height='32' rx='16' fill='#1d4ed8'/>
      <text x='16' y='21' text-anchor='middle' font-family='Arial' font-size='12' fill='#ffffff'>DH</text>
    </svg>`
  );
  const codesLine = Array.isArray(clinicalCodes) && clinicalCodes.length > 0
    ? clinicalCodes.slice(0, 4).map(c => `${c.code} (${c.system})`).join(", ")
    : null;
  
  return (
    <div className={`flex gap-3 ${isDoctor ? "" : "flex-row-reverse"} max-w-4xl mx-auto px-4 mb-6`}>
      {isDoctor && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarImage
            src={avatarSrc}
            alt="Dr. Hervix"
            onError={(e) => {
              try {
                (e.currentTarget as HTMLImageElement).src = `data:image/svg+xml;charset=utf-8,${fallbackSvg}`;
              } catch {}
            }}
          />
          <AvatarFallback className="bg-medical-blue text-white text-sm">
            DH
          </AvatarFallback>
        </Avatar>
      )}
      
      <div className={`flex flex-col ${isDoctor ? "items-start" : "items-end"} max-w-[85%]`}>
        <div
          className={`px-4 py-3 rounded-2xl ${
            isDoctor
              ? "bg-chat-bubble-doctor text-medical-text rounded-tl-md"
              : "bg-chat-bubble-user text-white rounded-tr-md"
          }`}
        >
          <p className="text-sm leading-relaxed">{message}</p>
          {codesLine && (
            <div className="mt-2 text-[11px] opacity-80">
              <span className="font-medium">Codes:</span> {codesLine}
            </div>
          )}
        </div>
        
        {timestamp && (
          <span className="text-xs text-medical-text-muted mt-1 px-1">
            {timestamp}
          </span>
        )}
        
        {/* Agent Progress for Doctor Messages */}
        {isDoctor && showAgentProgress && agentProgress && (
          <div className="mt-3 max-w-sm">
            <div className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm">
              <h4 className="font-medium text-sm text-gray-700 mb-2">Processing your request...</h4>
              <div className="space-y-2">
                {agentProgress.map((agent) => (
                  <div key={agent.id} className="flex items-center space-x-2">
                    <div className="flex-shrink-0">
                      {agent.status === 'completed' ? (
                        <div className="h-3 w-3 rounded-full bg-green-500" />
                      ) : agent.status === 'active' ? (
                        <div className="h-3 w-3 rounded-full bg-blue-500 animate-pulse" />
                      ) : (
                        <div className="h-3 w-3 rounded-full border-2 border-gray-300" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-medium text-gray-900">
                          {agent.name}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                          agent.status === 'completed' ? 'bg-green-100 text-green-800' :
                          agent.status === 'active' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {agent.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500">
                        {agent.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              {currentAgent && (
                <div className="mt-2 text-center">
                  <span className="text-xs text-blue-600 font-medium">
                    Currently: {currentAgent}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};